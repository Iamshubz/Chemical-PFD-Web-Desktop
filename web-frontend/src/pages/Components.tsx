import React, { useState, useRef } from "react";
import {
  Button,
  Input,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  useDisclosure,
  Select,
  SelectItem,
  Card,
  CardBody,
  CardFooter,
  Image,
  Tooltip,
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@heroui/react";

import { useComponents } from "@/context/ComponentContext";
import { ComponentItem, Grip } from "@/components/Canvas/types";

export default function Components() {
  const {
    components,
    addComponent,
    updateComponent,
    deleteComponent,
    isLoading,
    error,
  } = useComponents();
  const { isOpen, onOpen, onOpenChange } = useDisclosure();

  // Local type for handling input state (allows strings for "62.0")
  type EditableGrip = Omit<Grip, "x" | "y"> & {
    x: string | number;
    y: string | number;
  };
  const [grips, setGrips] = useState<EditableGrip[]>([]);

  // Form State
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [iconFile, setIconFile] = useState<string | null>(null);
  const [svgFile, setSvgFile] = useState<string | null>(null);
  const [legend, setLegend] = useState("");
  const [suffix, setSuffix] = useState("");

  // UI View State
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [isGripEditorOpen, setIsGripEditorOpen] = useState(false);
  const [tempGrips, setTempGrips] = useState<EditableGrip[]>([]);
  const imageRef = useRef<HTMLImageElement>(null);

  // Edit State
  const [editingComponent, setEditingComponent] = useState<{
    category: string;
    name: string;
  } | null>(null);

  // Helpers
  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    type: "icon" | "svg",
  ) => {
    const file = e.target.files?.[0];

    if (file) {
      const reader = new FileReader();

      reader.onloadend = () => {
        if (type === "icon") setIconFile(reader.result as string);
        else {
          setSvgFile(reader.result as string);
          if (e.target.files) {
            // Flush any existing grips when a completely new SVG is loaded 
            setGrips([]);
            setTempGrips([]);
            setIsGripEditorOpen(true);
          }
        }
      };
      reader.readAsDataURL(file);
    }
  };

  const handleEditorImageClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const xPercent = parseFloat(((x / rect.width) * 100).toFixed(4));
    const yPercent = parseFloat(((y / rect.height) * 100).toFixed(4));

    const clampedX = Math.max(0, Math.min(100, xPercent));
    const clampedY = Math.max(0, Math.min(100, yPercent));

    let side: "top" | "bottom" | "left" | "right" = "right";
    const distTop = clampedY;
    const distBottom = 100 - clampedY;
    const distLeft = clampedX;
    const distRight = 100 - clampedX;
    const minDist = Math.min(distTop, distBottom, distLeft, distRight);

    if (minDist === distTop) side = "top";
    else if (minDist === distBottom) side = "bottom";
    else if (minDist === distLeft) side = "left";
    else if (minDist === distRight) side = "right";

    setTempGrips([...tempGrips, { x: clampedX, y: 100 - clampedY, side }]);
  };

  const removeTempGrip = (index: number, e: React.MouseEvent) => {
    e.stopPropagation();
    const newGrips = tempGrips.filter((_, i) => i !== index);
    setTempGrips(newGrips);
  };

  const openGripEditor = () => {
    setTempGrips([...grips]);
    setIsGripEditorOpen(true);
  };

  const saveGripsFromEditor = () => {
    setGrips(tempGrips);
    setIsGripEditorOpen(false);
  };

  // Open modal specific for editing
  const handleEdit = (catName: string, item: ComponentItem) => {
    setEditingComponent({ category: catName, name: item.name });

    // Prefill form
    setName(item.name);
    setCategory(catName);
    setNewCategory("");
    setLegend(item.legend || "");
    setSuffix(item.suffix || "");
    setIconFile(
      typeof item.icon === "string" ? item.icon : (item.icon as any)?.src || "",
    );
    setSvgFile(
      typeof item.svg === "string" ? item.svg : (item.svg as any)?.src || "",
    );

    const initialGrips = item.grips ? item.grips.map((g) => ({ ...g })) : [];

    setGrips(initialGrips);
    setTempGrips(initialGrips);

    onOpen();
  };

  // Open modal for new
  const handleAddNew = () => {
    setEditingComponent(null);
    setName("");
    setCategory("");
    setNewCategory("");
    setLegend("");
    setSuffix("");
    setIconFile(null);
    setSvgFile(null);
    setGrips([]);
    setTempGrips([]);
    onOpen();
  };

  const handleDelete = async (onClose: () => void) => {
    if (!editingComponent) return;
    if (
      window.confirm(
        `Are you sure you want to delete "${editingComponent.name}"? This cannot be undone.`,
      )
    ) {
      try {
        await deleteComponent(editingComponent.category, editingComponent.name);
        alert("Component deleted successfully!");
        onClose();
      } catch (err: any) {
        alert(`Error: ${err.message || "Failed to delete component"}`);
      }
    }
  };

  const handleSubmit = async (onClose: () => void) => {
    if (!name || (!category && !newCategory)) return;

    const finalCategory = newCategory || category;

    // Clean grips to ensure they are numbers for the final object
    const cleanGrips: Grip[] = grips.map((g) => ({
      ...g,
      x: typeof g.x === "string" ? parseFloat(g.x) || 0 : g.x,
      y: typeof g.y === "string" ? parseFloat(g.y) || 0 : g.y,
    }));

    // Construct new component object as per requirements
    const newComponent: ComponentItem = {
      id: 0,
      name,
      icon: iconFile || "",
      svg: svgFile || iconFile || "", // Fallback to icon if SVG not provided
      class: finalCategory,
      object: name.replace(/\s+/g, ""),
      args: [],
      grips: cleanGrips,
      legend,
      suffix,
    };

    try {
      if (editingComponent) {
        await updateComponent(
          editingComponent.category,
          editingComponent.name,
          finalCategory,
          newComponent,
        );
        alert("Component updated successfully!");
      } else {
        await addComponent(finalCategory, newComponent);
        alert("Component created successfully!");
      }

      // Reset form
      setName("");
      setCategory("");
      setNewCategory("");
      setIconFile(null);
      setSvgFile(null);
      setLegend("");
      setSuffix("");
      setGrips([]);
      setEditingComponent(null);
      onClose();
    } catch (err: any) {
      alert(`Error: ${err.message || "Failed to save component"}`);
    }
  };

  const categories = Object.keys(components);
  const isFormValid = name.trim() !== "" && (category || newCategory) && iconFile && svgFile;

  return (
    <>
      <div className="p-8 h-full overflow-y-auto bg-gray-50 dark:bg-gray-900">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 dark:text-white">
            Component Library
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Manage and add custom components
          </p>
        </div>
        <Button color="primary" onPress={handleAddNew}>
          Add Component
        </Button>
      </div>

      <div className="space-y-8">
        {isLoading ? (
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <p className="text-red-500 dark:text-red-400 mb-4">{error}</p>
            <Button color="primary" onPress={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        ) : Object.keys(components).length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              No components yet. Click "Add Component" to create your first
              component.
            </p>
          </div>
        ) : (
          Object.entries(components).map(([catName, items]) => (
            <div key={catName}>
              <h2 className="text-xl font-semibold mb-4 text-gray-700 dark:text-gray-300 border-b pb-2 border-gray-200 dark:border-gray-700">
                {catName}
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {Object.values(items).map((item) => (
                  <Tooltip
                    key={item.name}
                    content={
                      <div className="text-xs">
                        <div className="font-bold">{item.name}</div>
                      </div>
                    }
                  >
                    <Card className="border-none bg-white dark:bg-gray-800 shadow-sm hover:shadow-md group relative">
                      <CardBody className="p-4 flex items-center justify-center bg-gray-50/50 dark:bg-gray-900/50">
                        <div className="w-16 h-16 flex items-center justify-center">
                          <Image
                            src={
                              typeof item.icon === "string"
                                ? item.icon
                                : (item.icon as any)?.src || item.icon
                            } // Handle imported image module vs string
                            alt={item.name}
                            className="max-w-full max-h-full object-contain"
                            radius="none"
                          />
                        </div>
                      </CardBody>
                      <CardFooter className="justify-between">
                        <div className="text-small font-medium truncate w-full text-center text-gray-700 dark:text-gray-300">
                          {item.name}
                        </div>
                        <Button
                          isIconOnly
                          aria-label="Edit"
                          className="absolute top-1 right-1 opacity-100 group-hover:opacity-100 transition-opacity bg-white/50 backdrop-blur-sm z-20"
                          size="sm"
                          variant="light"
                          onPress={() => {
                            handleEdit(catName, item);
                          }}
                        >
                          <span className="text-lg">✎</span>
                        </Button>
                      </CardFooter>
                    </Card>
                  </Tooltip>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Add Component Modal */}
      <Modal
        isOpen={isOpen}
        scrollBehavior="inside"
        size="3xl"
        onOpenChange={onOpenChange}
        isDismissable={false}
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex justify-between items-center w-full pr-8">
                <div className="flex flex-col gap-1">
                  {editingComponent
                    ? `Edit ${editingComponent.name}`
                    : "Add New Component"}
                </div>
                <Popover isOpen={isHelpOpen} onOpenChange={setIsHelpOpen} placement="bottom-end">
                  <PopoverTrigger>
                    <Button
                      isIconOnly
                      variant="light"
                      className="text-gray-500 hover:text-primary transition-colors text-xl"
                      aria-label="Toggle Component Help"
                    >
                      ℹ️
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[500px]">
                    <div className="p-4 bg-white dark:bg-gray-900 rounded-xl text-sm relative">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                        onPress={() => setIsHelpOpen(false)}
                      >
                        ✕
                      </Button>
                      <h4 className="font-semibold text-blue-800 dark:text-blue-300 mb-4 flex items-center gap-2 text-base w-11/12">
                        Component Requirements Guide
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4 text-gray-600 dark:text-gray-300 leading-relaxed">
                        <div>
                          <strong className="block text-gray-800 dark:text-gray-100 mb-1">File Requirements</strong>
                          <ul className="list-disc pl-4 space-y-1 text-xs">
                            <li><b>PNG:</b> Displayed as the thumbnail in sidebars.</li>
                            <li><b>SVG:</b> Rendered on the piping canvas.</li>
                          </ul>
                        </div>
                        <div>
                          <strong className="block text-gray-800 dark:text-gray-100 mb-1">Label Generation</strong>
                          <p className="text-xs">Format: <code>Legend-Count-Suffix</code> (e.g., <code>P-01-A</code>) representing type and chronological order.</p>
                        </div>
                        <div>
                          <strong className="block text-gray-800 dark:text-gray-100 mb-1">Field Definitions</strong>
                          <ul className="list-disc pl-4 space-y-1 text-xs">
                            <li><b>Legend:</b> The base prefix (e.g., 'HX').</li>
                            <li><b>Suffix:</b> An optional trailing specifier (e.g., 'A').</li>
                          </ul>
                        </div>
                        <div>
                          <strong className="block text-gray-800 dark:text-gray-100 mb-1">Grips & Connectors</strong>
                          <p className="text-xs">Anchor points that snap pipes and lines to the boundaries of this component.</p>
                        </div>
                      </div>
                    </div>
                  </PopoverContent>
                </Popover>
              </ModalHeader>
              <ModalBody>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Left Column: Form Fields */}
                  <div className="space-y-4">
                    <Tooltip content="Primary display name, visible in the library and toolbars." placement="top-start" delay={600}>
                      <div className="block w-full">
                        <Input
                          isRequired
                          label="Component Name"
                          placeholder="e.g. My Custom Heat Exchanger"
                          value={name}
                          onValueChange={setName}
                        />
                      </div>
                    </Tooltip>

                    <Tooltip content="Groups identical components under a single tab." placement="top-start" delay={600}>
                      <div className="block w-full">
                        <Select
                          label="Category"
                          placeholder="Select category"
                          selectedKeys={category ? [category] : []}
                          onChange={(e) => {
                            setCategory(e.target.value);
                            setNewCategory("");
                          }}
                        >
                          {categories.map((cat) => (
                            <SelectItem key={cat}>{cat}</SelectItem>
                          ))}
                        </Select>
                      </div>
                    </Tooltip>

                    <Tooltip content="Create a brand new category tab." placement="top-start" delay={600}>
                      <div className="block w-full">
                        <Input
                          label="New Category (Optional)"
                          placeholder="Or create new..."
                          value={newCategory}
                          onValueChange={(val) => {
                            setNewCategory(val);
                            if (val) setCategory("");
                          }}
                        />
                      </div>
                    </Tooltip>

                    <div className="flex gap-4">
                      <Tooltip content="Base prefix for auto-generated labels (e.g. HEX)." placement="top-start" delay={600}>
                        <div className="flex-1">
                          <Input
                            label="Legend"
                            placeholder="e.g. HEX"
                            value={legend}
                            onValueChange={setLegend}
                          />
                        </div>
                      </Tooltip>
                      <Tooltip content="Optional trailing specifier (e.g. A/B)." placement="top-start" delay={600}>
                        <div className="flex-1">
                          <Input
                            label="Suffix"
                            placeholder="e.g. A/B"
                            value={suffix}
                            onValueChange={setSuffix}
                          />
                        </div>
                      </Tooltip>
                    </div>

                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                      <label className="block text-sm font-medium mb-2 text-gray-600 dark:text-gray-400">
                        Component Images
                      </label>
                      <div className="flex flex-col gap-3">
                        <Tooltip content="Required: Image used for library thumbnail." placement="top-start" delay={600}>
                          <div className="block w-full">
                            <Input
                              accept="image/png"
                              label="Toolbar Icon (PNG)"
                              labelPlacement="outside"
                              type="file"
                              onChange={(e) => handleFileChange(e, "icon")}
                            />
                          </div>
                        </Tooltip>
                        <Tooltip content="Required: Vector graphic rendered on canvas." placement="top-start" delay={600}>
                          <div className="block w-full">
                            <Input
                              accept="image/svg+xml,image/png,image/jpeg"
                              label="Canvas SVG"
                              labelPlacement="outside"
                              type="file"
                              onChange={(e) => handleFileChange(e, "svg")}
                            />
                          </div>
                        </Tooltip>
                      </div>
                    </div>
                    
                    {/* Final Component Preview */}
                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-white dark:bg-gray-800 shadow-sm mt-4">
                       <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                         Component Final Preview
                       </h3>
                       <div className="flex items-center gap-4">
                          <div className="w-16 h-16 border rounded-lg bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700 flex items-center justify-center p-2 text-gray-400">
                            {iconFile ? <img src={iconFile} alt="Toolbar Icon" className="max-w-full max-h-full object-contain" /> : <span className="text-xs">PNG</span>}
                          </div>
                          <div className="flex flex-col justify-center">
                             <p className="text-xs text-gray-400 mb-1">Generated Label Frame</p>
                             <div className="px-3 py-1 bg-gray-100 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded font-mono text-sm font-bold text-primary flex items-center gap-1">
                               <span>{legend || "???"}</span>
                               <span className="text-gray-400">-</span>
                               <span>01</span>
                               {suffix && (
                                 <>
                                   <span className="text-gray-400">-</span>
                                   <span>{suffix}</span>
                                 </>
                               )}
                             </div>
                          </div>
                       </div>
                    </div>

                  </div>

                  {/* Right Column: Grip Editor Summary */}
                  <div className="space-y-4">
                    <h3 className="font-semibold text-gray-700 dark:text-gray-300">
                      Grips & Connectors
                    </h3>
                    
                    <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700">
                      <div className="flex justify-between items-center mb-4">
                        <span className="text-sm font-medium">Total Grips Configured:</span>
                        <span className="text-xl font-bold text-primary">{grips.length}</span>
                      </div>
                      
                      <Button
                        color="primary"
                        variant="flat"
                        className="w-full"
                        onPress={openGripEditor}
                        isDisabled={!svgFile}
                        startContent={<span>🎯</span>}
                      >
                        {grips.length > 0 ? "Edit Grips" : "Configure Grips"}
                      </Button>
                      
                      {!svgFile && (
                        <p className="text-xs text-gray-400 mt-2 text-center">
                          Upload a Canvas SVG to configure grips
                        </p>
                      )}
                    </div>
                    
                    {/* Small preview of the SVG with purely visual dots, NO interactivity */}
                    {svgFile && (
                      <div className="relative w-full aspect-video bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 flex items-center justify-center overflow-hidden p-4 pointer-events-none">
                        <div className="relative inline-block">
                          <img
                            alt="Grip Preview"
                            className="w-auto h-auto max-w-full max-h-[160px]"
                            src={svgFile}
                          />
                          {grips.map((grip, idx) => (
                             <div
                                key={idx}
                                className="absolute w-3 h-3 -ml-1.5 -mt-1.5 rounded-full bg-primary ring-2 ring-white select-none pointer-events-none"
                                style={{
                                  left: `${grip.x}%`,
                                  top: `${100 - Number(grip.y)}%`,
                                }}
                              />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </ModalBody>
              <ModalFooter className="flex justify-between items-center">
                <div>
                  {editingComponent && (
                    <Button
                      color="danger"
                      variant="flat"
                      onPress={() => handleDelete(onClose)}
                    >
                      Delete Component
                    </Button>
                  )}
                </div>
                <div className="flex flex-col items-end gap-2">
                  {!isFormValid && (
                    <span className="text-xs text-danger pr-1">
                      *Please fill required fields and upload both PNG and SVG.
                    </span>
                  )}
                  <div className="flex gap-2">
                    <Button color="danger" variant="light" onPress={onClose}>
                      Cancel
                    </Button>
                    <Button color="primary" onPress={() => handleSubmit(onClose)} isDisabled={!isFormValid}>
                      {editingComponent ? "Save Changes" : "Create Component"}
                    </Button>
                  </div>
                </div>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>

      {/* Interactive Grip Editor Popup */}
      <Modal 
        isOpen={isGripEditorOpen} 
        onOpenChange={setIsGripEditorOpen}
        size="3xl"
        isDismissable={false}
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1">Interactive Grip Editor</ModalHeader>
          <ModalBody>
            <p className="text-sm text-gray-500 mb-2">
              Click anywhere inside the highlighted boundary to add a connection point. Click an existing point to remove it.
            </p>
            <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 flex justify-center items-center overflow-auto p-8 min-h-[40vh] max-h-[60vh]">
               {svgFile && (
                  <div
                    className="relative inline-block cursor-crosshair group shadow-sm ring-1 ring-gray-400 dark:ring-gray-500 bg-white dark:bg-gray-900"
                    onClick={handleEditorImageClick}
                  >
                    <img
                      ref={imageRef}
                      alt="Interactive Grip Area"
                      className="w-auto h-auto min-w-[300px] max-w-full"
                      style={{ maxHeight: '50vh' }}
                      src={svgFile}
                      draggable={false}
                    />

                    {tempGrips.map((grip, idx) => (
                      <div
                        key={idx}
                        className="absolute w-6 h-6 -ml-3 -mt-3 rounded-full flex items-center justify-center text-xs font-bold border-2 bg-primary text-white border-white ring-2 ring-primary/50 transition-transform hover:scale-125 hover:bg-danger hover:border-danger hover:ring-danger/50 cursor-pointer shadow-md"
                        style={{
                          left: `${grip.x}%`,
                          top: `${100 - Number(grip.y)}%`,
                        }}
                        onClick={(e) => removeTempGrip(idx, e)}
                        title="Click to remove"
                      >
                        {idx + 1}
                      </div>
                    ))}
                  </div>
               )}
            </div>
            <div className="flex justify-between items-center mt-2 mb-1">
               <span className="font-semibold text-gray-700 dark:text-gray-300">
                  Total Connectors: {tempGrips.length}
               </span>
            </div>
          </ModalBody>
          <ModalFooter>
             <Button color="danger" variant="light" onPress={() => setIsGripEditorOpen(false)}>
                Cancel
             </Button>
             <Button color="primary" onPress={saveGripsFromEditor}>
                Confirm & Save
             </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
}

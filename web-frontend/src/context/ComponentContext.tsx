import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";

import { ComponentItem } from "@/components/Canvas/types";
import {
  fetchComponents,
  createComponent,
  updateComponent as apiUpdateComponent,
  deleteComponent as apiDeleteComponent,
  type ComponentData,
} from "@/utils/componentApi";

interface ComponentContextType {
  components: Record<string, Record<string, ComponentItem>>;
  isLoading: boolean;
  error: string | null;
  addComponent: (category: string, component: ComponentItem) => Promise<void>;
  updateComponent: (
    oldCategory: string,
    oldName: string,
    newCategory: string,
    newComponent: ComponentItem,
  ) => Promise<void>;
  deleteComponent: (category: string, name: string) => Promise<void>;
  refreshComponents: () => Promise<void>;
}

const ComponentContext = createContext<ComponentContextType | undefined>(
  undefined,
);

// Convert backend ComponentData to frontend ComponentItem format
function convertToComponentItem(data: ComponentData): ComponentItem {
  return {
    id: data.id ?? 0,
    name: data.name,
    icon: data.png_url || data.svg_url || "",
    svg: data.svg_url || "",
    png: data.png_url,
    class: data.parent, // category
    object: data.object,
    args: [],
    grips: data.grips,
    legend: data.legend,
    suffix: data.suffix,
    isCustom: false, // Not needed anymore since all are user-created
  };
}

// Convert ComponentData array to categorized component structure
function categorizeComponents(
  components: ComponentData[],
): Record<string, Record<string, ComponentItem>> {
  const categorized: Record<string, Record<string, ComponentItem>> = {};

  components.forEach((comp) => {
    const category = comp.parent || "Uncategorized";

    if (!categorized[category]) {
      categorized[category] = {};
    }
    categorized[category][comp.name] = convertToComponentItem(comp);
  });

  return categorized;
}

// Convert base64 data URL to File object
function dataURLtoFile(dataurl: string, filename: string): File {
  const arr = dataurl.split(",");
  const mime = arr[0].match(/:(.*?);/)?.[1] || "application/octet-stream";
  const bstr = atob(arr[1]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);

  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }

  return new File([u8arr], filename, { type: mime });
}

export const ComponentProvider = ({ children }: { children: ReactNode }) => {
  const [components, setComponents] = useState<
    Record<string, Record<string, ComponentItem>>
  >({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch components from backend on mount
  const refreshComponents = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchComponents();
      const categorized = categorizeComponents(data);

      setComponents(categorized);
    } catch (err: any) {
      console.error("Failed to fetch components:", err);
      // Only set error for actual failures, not for empty lists
      if (err.response?.status !== 404) {
        setError(
          err.response?.data?.detail ||
            err.message ||
            "Failed to load components",
        );
      }
      // Set empty components on error
      setComponents({});
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshComponents();
  }, []);

  const addComponent = async (category: string, component: ComponentItem) => {
    try {
      setError(null);

      // Convert data URLs to File objects if needed
      let svgFile: File | undefined;
      let pngFile: File | undefined;

      if (
        component.svg &&
        typeof component.svg === "string" &&
        component.svg.startsWith("data:")
      ) {
        svgFile = dataURLtoFile(component.svg, `${component.name}.svg`);
      }
      if (
        component.icon &&
        typeof component.icon === "string" &&
        component.icon.startsWith("data:")
      ) {
        pngFile = dataURLtoFile(component.icon, `${component.name}.png`);
      }

      const created = await createComponent({
        name: component.name,
        parent: category,
        legend: component.legend || "",
        suffix: component.suffix || "",
        object: component.object || component.name.replace(/\s+/g, ""),
        grips: component.grips || [],
        svg: svgFile,
        png: pngFile,
      });

      // Update local state
      setComponents((prev) => {
        const updated = { ...prev };

        if (!updated[category]) {
          updated[category] = {};
        }
        updated[category][created.name] = convertToComponentItem(created);

        return updated;
      });
    } catch (err: any) {
      console.error("Failed to create component:", err);
      setError(err.message || "Failed to create component");
      throw err;
    }
  };

  const deleteComponent = async (category: string, name: string) => {
    try {
      setError(null);

      // Find component ID
      const comp = components[category]?.[name];

      if (!comp || !comp.id) {
        throw new Error("Component not found");
      }

      await apiDeleteComponent(comp.id);

      // Update local state
      setComponents((prev) => {
        const updated = { ...prev };

        if (updated[category]) {
          const { [name]: deleted, ...rest } = updated[category];

          updated[category] = rest;

          // Remove category if empty
          if (Object.keys(updated[category]).length === 0) {
            delete updated[category];
          }
        }

        return updated;
      });
    } catch (err: any) {
      console.error("Failed to delete component:", err);
      setError(err.message || "Failed to delete component");
      throw err;
    }
  };

  const updateComponent = async (
    oldCategory: string,
    oldName: string,
    newCategory: string,
    newComponent: ComponentItem,
  ) => {
    try {
      setError(null);

      // Find component ID
      const comp = components[oldCategory]?.[oldName];

      if (!comp || !comp.id) {
        throw new Error("Component not found");
      }

      // Convert data URLs to File objects if needed
      let svgFile: File | undefined;
      let pngFile: File | undefined;

      if (
        newComponent.svg &&
        typeof newComponent.svg === "string" &&
        newComponent.svg.startsWith("data:")
      ) {
        svgFile = dataURLtoFile(newComponent.svg, `${newComponent.name}.svg`);
      }
      if (
        newComponent.icon &&
        typeof newComponent.icon === "string" &&
        newComponent.icon.startsWith("data:")
      ) {
        pngFile = dataURLtoFile(newComponent.icon, `${newComponent.name}.png`);
      }

      const updated = await apiUpdateComponent(comp.id, {
        name: newComponent.name,
        parent: newCategory,
        legend: newComponent.legend,
        suffix: newComponent.suffix,
        object: newComponent.object || newComponent.name.replace(/\s+/g, ""),
        grips: newComponent.grips,
        svg: svgFile,
        png: pngFile,
      });

      // Update local state
      setComponents((prev) => {
        const next = { ...prev };

        // Remove from old category
        if (next[oldCategory]) {
          const { [oldName]: deleted, ...rest } = next[oldCategory];

          next[oldCategory] = rest;

          // Remove old category if empty
          if (Object.keys(next[oldCategory]).length === 0) {
            delete next[oldCategory];
          }
        }

        // Add to new category
        if (!next[newCategory]) {
          next[newCategory] = {};
        }
        next[newCategory][updated.name] = convertToComponentItem(updated);

        return next;
      });
    } catch (err: any) {
      console.error("Failed to update component:", err);
      setError(err.message || "Failed to update component");
      throw err;
    }
  };

  return (
    <ComponentContext.Provider
      value={{
        components,
        isLoading,
        error,
        addComponent,
        updateComponent,
        deleteComponent,
        refreshComponents,
      }}
    >
      {children}
    </ComponentContext.Provider>
  );
};

export const useComponents = () => {
  const context = useContext(ComponentContext);

  if (!context) {
    throw new Error("useComponents must be used within a ComponentProvider");
  }

  return context;
};

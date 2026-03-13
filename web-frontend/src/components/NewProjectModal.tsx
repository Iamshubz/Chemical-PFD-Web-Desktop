import { useState } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  Textarea,
} from "@heroui/react";

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string, description: string) => void;
}

export function NewProjectModal({
  isOpen,
  onClose,
  onCreate,
}: NewProjectModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [nameError, setNameError] = useState("");

  const handleCreate = () => {
    // Validate project name
    if (!name.trim()) {
      setNameError("Project name is required");

      return;
    }

    onCreate(name.trim(), description.trim());

    // Reset form
    setName("");
    setDescription("");
    setNameError("");
    onClose();
  };

  const handleClose = () => {
    // Reset form on close
    setName("");
    setDescription("");
    setNameError("");
    onClose();
  };

  return (
    <Modal isOpen={isOpen} placement="center" size="lg" onClose={handleClose}>
      <ModalContent>
        {() => (
          <>
            <ModalHeader className="flex flex-col gap-1">
              Create New Project
            </ModalHeader>
            <ModalBody>
              <div className="flex flex-col gap-4">
                <Input
                  autoFocus
                  isRequired
                  errorMessage={nameError}
                  isInvalid={!!nameError}
                  label="Project Name"
                  placeholder="Enter project name"
                  value={name}
                  variant="bordered"
                  onChange={(e) => {
                    setName(e.target.value);
                    setNameError("");
                  }}
                />
                <Textarea
                  label="Description"
                  maxRows={6}
                  minRows={3}
                  placeholder="Enter project description (optional)"
                  value={description}
                  variant="bordered"
                  onChange={(e) => setDescription(e.target.value)}
                />
                <p className="text-xs text-gray-500">
                  You can edit the project name and description later from the
                  editor.
                </p>
              </div>
            </ModalBody>
            <ModalFooter>
              <Button color="danger" variant="light" onPress={handleClose}>
                Cancel
              </Button>
              <Button color="primary" onPress={handleCreate}>
                Create Project
              </Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
}

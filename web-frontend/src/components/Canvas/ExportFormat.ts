import { CanvasItem, Connection } from "./types";

/**
 * Diagram File Format (Version 1.0)
 *
 * This format includes:
 * - Canvas items with their positions and properties
 * - Connections between items
 * - Metadata for versioning and compatibility
 * - Grid and viewport settings
 */

export interface DiagramFileFormat {
  version: string;
  metadata: {
    name: string;
    description?: string;
    createdAt: string;
    updatedAt: string;
    author?: string;
    tags?: string[];
  };
  canvas: {
    width: number;
    height: number;
    backgroundColor: string;
    grid: {
      enabled: boolean;
      size: number;
      color: string;
    };
    viewport: {
      scale: number;
      position: { x: number; y: number };
    };
  };
  items: CanvasItem[];
  connections: Connection[];
}

/**
 * Current version of the file format
 */
export const CURRENT_VERSION = "1.0.0";

/**
 * Create a new diagram file
 */
export function createDiagramFile(
  items: CanvasItem[],
  connections: Connection[],
  options: {
    name?: string;
    description?: string;
    backgroundColor?: string;
    gridEnabled?: boolean;
    gridSize?: number;
    author?: string;
    tags?: string[];
  } = {},
): DiagramFileFormat {
  const now = new Date().toISOString();

  return {
    version: CURRENT_VERSION,
    metadata: {
      name: options.name || "Untitled Diagram",
      description: options.description,
      createdAt: now,
      updatedAt: now,
      author: options.author,
      tags: options.tags || [],
    },
    canvas: {
      width: 1200, // Default canvas size
      height: 800,
      backgroundColor: options.backgroundColor || "#ffffff",
      grid: {
        enabled: options.gridEnabled !== undefined ? options.gridEnabled : true,
        size: options.gridSize || 20,
        color: "#e5e7eb",
      },
      viewport: {
        scale: 1,
        position: { x: 0, y: 0 },
      },
    },
    items,
    connections,
  };
}

/**
 * Validate a diagram file
 */
export function validateDiagramFile(data: any): data is DiagramFileFormat {
  if (!data || typeof data !== "object") return false;
  if (typeof data.version !== "string") return false;
  if (!data.metadata || typeof data.metadata !== "object") return false;
  if (typeof data.metadata.name !== "string") return false;
  if (!data.canvas || typeof data.canvas !== "object") return false;
  if (!Array.isArray(data.items)) return false;
  if (!Array.isArray(data.connections)) return false;

  return true;
}

/**
 * Migrate older versions to current format
 */
export function migrateDiagramFile(data: any): DiagramFileFormat {
  if (!data.version) {
    // Assume version 1.0.0
    return {
      version: CURRENT_VERSION,
      metadata: {
        name: data.name || "Untitled Diagram",
        description: data.description,
        createdAt: data.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        author: data.author,
        tags: data.tags || [],
      },
      canvas: {
        width: data.canvas?.width || 1200,
        height: data.canvas?.height || 800,
        backgroundColor: data.canvas?.backgroundColor || "#ffffff",
        grid: {
          enabled:
            data.canvas?.grid?.enabled !== undefined
              ? data.canvas.grid.enabled
              : true,
          size: data.canvas?.grid?.size || 20,
          color: data.canvas?.grid?.color || "#e5e7eb",
        },
        viewport: {
          scale: data.canvas?.viewport?.scale || 1,
          position: data.canvas?.viewport?.position || { x: 0, y: 0 },
        },
      },
      items: data.items || [],
      connections: data.connections || [],
    };
  }

  // Add future migration logic here as version increases
  return data as DiagramFileFormat;
}

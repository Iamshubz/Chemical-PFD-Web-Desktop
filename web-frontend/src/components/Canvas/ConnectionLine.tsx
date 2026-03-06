// src/components/Canvas/ConnectionLine.tsx

import { Path, RegularPolygon, Circle } from "react-konva";
import { KonvaEventObject } from "konva/lib/Node";

import { Connection, CanvasItem } from "./types";

interface ConnectionLineProps {
  connection: Connection;
  points: { x: number, y: number }[];
  items?: CanvasItem[];
  isSelected?: boolean;
  onSelect?: (e: KonvaEventObject<MouseEvent>) => void;
  onWaypointDrag?: (index: number, pos: { x: number, y: number }) => void;
  arrowAngle?: number;
  targetPosition?: { x: number; y: number };
}

export const ConnectionLine = ({
  connection,
  points,
  pathData,
  isSelected = false,
  onSelect,
  onWaypointDrag,
  arrowAngle,
  targetPosition,
}: ConnectionLineProps & { pathData?: string }) => {
  // Safety check
  if (!pathData) return null;

  // Handlers for hover effects
  const handleMouseEnter = (e: KonvaEventObject<MouseEvent>) => {
    const stage = e.target.getStage();

    if (stage) {
      stage.container().style.cursor = "pointer";
    }
  };

  const handleMouseLeave = (e: KonvaEventObject<MouseEvent>) => {
    const stage = e.target.getStage();

    if (stage) {
      stage.container().style.cursor = "default";
    }
  };

  return (
    <>
      {/* 1. HIT AREA (Invisible) */}
      <Path
        data={pathData}
        stroke="transparent"
        strokeWidth={20} // 20px wide clickable area
        onMouseDown={(e) => {
          e.cancelBubble = true;
          onSelect?.(e);
        }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onTap={onSelect}
      />

      {/* 2. VISIBLE LINE */}
      <Path
        data={pathData}
        lineCap="round"
        lineJoin="round"
        listening={false}
        shadowBlur={isSelected ? 4 : 0}
        shadowColor="black"
        shadowOpacity={0.3}
        stroke={isSelected ? "#3b82f6" : "#64748b"}
        strokeWidth={isSelected ? 3 : 2}
      />

      {/* 3. ARROW HEAD */}
      {targetPosition && arrowAngle !== undefined && (
        <RegularPolygon
          fill={isSelected ? "#3b82f6" : "#64748b"}
          listening={false}
          radius={6}
          rotation={arrowAngle}
          sides={3}
          x={targetPosition.x}
          y={targetPosition.y}
        />
      )}
      {/* 4. DRAG HANDLES */}
      {isSelected && points && points.map((p, i) => (
        <Circle
          key={i}
          x={p.x}
          y={p.y}
          radius={6}
          fill="#00e5ff"
          stroke="#000"
          strokeWidth={1}
          draggable
          onDragMove={(e) => {
            const dx = Math.abs(e.target.x() - p.x);
            const dy = Math.abs(e.target.y() - p.y);

            // Lock axis based on which way they drag more for clean 90-degree wires
            if (dx > dy) {
              e.target.y(p.y);
            } else {
              e.target.x(p.x);
            }

            onWaypointDrag?.(i, {
              x: e.target.x(),
              y: e.target.y()
            });
          }}
          onMouseEnter={(e) => {
            const stage = e.target.getStage();
            if (stage) stage.container().style.cursor = "move";
          }}
          onMouseLeave={(e) => {
            const stage = e.target.getStage();
            if (stage) stage.container().style.cursor = "default";
          }}
        />
      ))}
    </>
  );
};

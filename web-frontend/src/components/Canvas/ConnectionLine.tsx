// src/components/Canvas/ConnectionLine.tsx

import { Path, RegularPolygon, Line } from "react-konva";
import { KonvaEventObject } from "konva/lib/Node";

import { CanvasItem } from "./types";

import { LineSegment } from "../../utils/pathfinding/types";
import { getPaddedObstacleRects } from "../../utils/pathfinding/obstacles";

interface ConnectionLineProps {
  items?: CanvasItem[];
  isSelected?: boolean;
  onSelect?: (e: KonvaEventObject<MouseEvent>) => void;
  onSegmentDragEnd?: (segment: LineSegment, dx: number, dy: number) => void;
  arrowAngle?: number;
  targetPosition?: { x: number; y: number };
  segments?: LineSegment[];
}

export const ConnectionLine = ({
  pathData,
  isSelected = false,
  items,
  onSelect,
  onSegmentDragEnd,
  arrowAngle,
  targetPosition,
  segments,
}: ConnectionLineProps & { pathData?: string }) => {
  // Safety check
  if (!pathData) return null;

  const paddedRects = items ? getPaddedObstacleRects(items, 20) : [];

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
      {/* 4. DRAG SEGMENTS */}
      {isSelected && segments &&
        segments.map((seg, i) => {
          return (
            <Line
              key={`seg-${i}`}
              points={[seg.p1.x, seg.p1.y, seg.p2.x, seg.p2.y]}
              stroke="transparent"
              strokeWidth={20}
              draggable
              dragBoundFunc={(pos) => {
                let boundedX = pos.x;
                let boundedY = pos.y;

                if (seg.type === 'vertical') {
                  const minY = Math.min(seg.p1.y, seg.p2.y);
                  const maxY = Math.max(seg.p1.y, seg.p2.y);
                  const startX = seg.p1.x; // original X  
                  const currentX = startX + pos.x; // proposed X

                  // Find obstacles that overlap vertically
                  const overlapping = paddedRects.filter(r => r.y < maxY && r.y + r.height > minY);
                  
                  if (pos.x < 0) { // dragging left
                     const leftBlockers = overlapping.filter(r => r.x + r.width <= startX);
                     const minXAllowed = leftBlockers.length > 0 ? Math.max(...leftBlockers.map(r => r.x + r.width)) : -Infinity;
                     if (currentX < minXAllowed) boundedX = minXAllowed - startX;
                  } else if (pos.x > 0) { // dragging right
                     const rightBlockers = overlapping.filter(r => r.x >= startX);
                     const maxXAllowed = rightBlockers.length > 0 ? Math.min(...rightBlockers.map(r => r.x)) : Infinity;
                     if (currentX > maxXAllowed) boundedX = maxXAllowed - startX;
                  }
                  
                  return { x: boundedX, y: 0 }; 
                } else {
                  const minX = Math.min(seg.p1.x, seg.p2.x);
                  const maxX = Math.max(seg.p1.x, seg.p2.x);
                  const startY = seg.p1.y;
                  const currentY = startY + pos.y;
                  
                  const overlapping = paddedRects.filter(r => r.x < maxX && r.x + r.width > minX);

                  if (pos.y < 0) { // dragging up
                     const upBlockers = overlapping.filter(r => r.y + r.height <= startY);
                     const minYAllowed = upBlockers.length > 0 ? Math.max(...upBlockers.map(r => r.y + r.height)) : -Infinity;
                     if (currentY < minYAllowed) boundedY = minYAllowed - startY;
                  } else if (pos.y > 0) { // dragging down
                     const downBlockers = overlapping.filter(r => r.y >= startY);
                     const maxYAllowed = downBlockers.length > 0 ? Math.min(...downBlockers.map(r => r.y)) : Infinity;
                     if (currentY > maxYAllowed) boundedY = maxYAllowed - startY;
                  }
                  
                  return { x: 0, y: boundedY }; 
                }
              }}
              onDragEnd={(e) => {
                const dx = e.target.x();
                const dy = e.target.y();
                e.target.position({ x: 0, y: 0 }); // Reset position visually
                if (Math.abs(dx) > 0 || Math.abs(dy) > 0) {
                  onSegmentDragEnd?.(seg, dx, dy);
                }
              }}
              onMouseEnter={(e) => {
                const stage = e.target.getStage();
                if (stage) {
                  stage.container().style.cursor = seg.type === 'horizontal' ? 'ns-resize' : 'ew-resize';
                }
              }}
              onMouseLeave={handleMouseLeave}
            />
          );
        })}
    </>
  );
};

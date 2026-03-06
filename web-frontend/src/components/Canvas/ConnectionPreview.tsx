import { Path, RegularPolygon } from "react-konva";

interface Point {
  x: number;
  y: number;
}

interface ConnectionPreviewProps {
  pathData: string | null;
  endPoint?: Point;
  arrowAngle?: number;
}

/**
 * Temporary dotted preview line while user is choosing target grip.
 * Purely visual. No interaction.
 */
export const ConnectionPreview = ({
  pathData,
  endPoint,
  arrowAngle,
}: ConnectionPreviewProps) => {
  if (!pathData) return null;

  return (
    <>
      {/* dotted preview wire */}
      <Path
        data={pathData}
        stroke="#94a3b8"
        strokeWidth={2}
        dash={[6, 6]}      // ← dotted effect
        lineCap="round"
        lineJoin="round"
        listening={false}
      />

      {/* optional arrow head */}
      {endPoint && arrowAngle !== undefined && (
        <RegularPolygon
          sides={3}
          radius={5}
          x={endPoint.x}
          y={endPoint.y}
          rotation={arrowAngle}
          fill="#94a3b8"
          listening={false}
        />
      )}
    </>
  );
};
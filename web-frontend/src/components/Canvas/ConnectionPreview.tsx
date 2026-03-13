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
        dash={[6, 6]} // ← dotted effect
        data={pathData}
        lineCap="round"
        lineJoin="round"
        listening={false}
        stroke="#94a3b8"
        strokeWidth={2}
      />

      {/* optional arrow head */}
      {endPoint && arrowAngle !== undefined && (
        <RegularPolygon
          fill="#94a3b8"
          listening={false}
          radius={5}
          rotation={arrowAngle}
          sides={3}
          x={endPoint.x}
          y={endPoint.y}
        />
      )}
    </>
  );
};

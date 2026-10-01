import { useThree } from "@react-three/fiber";

// A thin circle that always faces the camera: circle the subject on a claim ("perfect sphere"),
// recolour it on the twist (white -> red "It isn't"), bring it back green on the answer.
export const Ring = ({ opacity, color = "#ffffff", position = [0, 0, 0], radius = 1.1, width = 0.04 }: {
  opacity: number; color?: string; position?: [number, number, number]; radius?: number; width?: number;
}) => {
  const { camera } = useThree();
  if (opacity <= 0.001) return null;
  return (
    <mesh position={position} quaternion={camera.quaternion}>
      <ringGeometry args={[radius, radius + width, 128]} />
      <meshBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} />
    </mesh>
  );
};

export function useTimeline() {
  // Timeline scroll state managed locally in the Timeline component
  // This hook provides shared utilities

  const calculateInterval = (pixelsPerSecond: number): number => {
    if (pixelsPerSecond >= 40) return 1;
    if (pixelsPerSecond >= 15) return 2;
    if (pixelsPerSecond >= 8) return 5;
    if (pixelsPerSecond >= 4) return 10;
    if (pixelsPerSecond >= 2) return 30;
    return 60;
  };

  const timeAtPosition = (x: number, scrollOffset: number, pixelsPerSecond: number): number => {
    return (x + scrollOffset) / pixelsPerSecond;
  };

  const positionForTime = (seconds: number, scrollOffset: number, pixelsPerSecond: number): number => {
    return seconds * pixelsPerSecond - scrollOffset;
  };

  const getMarkerColor = (color: string): string => {
    const map: Record<string, string> = {
      yellow: "#eab308",
      red: "#ef4444",
      blue: "#3b82f6",
      green: "#22c55e",
      orange: "#f97316",
      purple: "#a855f7",
    };
    return map[color] ?? "#eab308";
  };

  return { calculateInterval, timeAtPosition, positionForTime, getMarkerColor };
}

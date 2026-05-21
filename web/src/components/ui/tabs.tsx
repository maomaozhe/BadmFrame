import { cn } from "@/utils";

interface TabsProps {
  value: string;
  onValueChange: (v: string) => void;
  children: React.ReactNode;
  className?: string;
}

function Tabs({ value, onValueChange, children, className }: TabsProps) {
  return (
    <div className={cn("flex gap-1", className)}>
      {children}
    </div>
  );
}

interface TabProps {
  value: string;
  activeValue: string;
  onSelect: (v: string) => void;
  children: React.ReactNode;
}

function Tab({ value, activeValue, onSelect, children }: TabProps) {
  return (
    <button
      onClick={() => onSelect(value)}
      className={cn(
        "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
        value === activeValue
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:text-foreground"
      )}
    >
      {children}
    </button>
  );
}

export { Tabs, Tab };

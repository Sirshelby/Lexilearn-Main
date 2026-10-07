import { Snail, Volume2 } from "lucide-react";
import { usePreferences } from "../context/PreferencesContext";

export function SpeakButton({
  text,
  label = "Hear it",
  slow = false,
  className = "btn btn-quiet",
}: {
  text: string;
  label?: string;
  slow?: boolean;
  className?: string;
}) {
  const { say } = usePreferences();
  const Icon = slow ? Snail : Volume2;
  return (
    <button type="button" className={className} onClick={() => void say(text, { slow })}>
      <Icon size={20} aria-hidden="true" />
      {label}
    </button>
  );
}

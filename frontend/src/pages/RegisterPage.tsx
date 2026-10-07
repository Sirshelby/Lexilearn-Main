import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthLayout } from "../components/AuthLayout";
import { ErrorNote } from "../components/Feedback";
import { PasswordField } from "../components/PasswordField";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import type { User } from "../lib/types";

const ACCOUNT_TYPES: { value: User["account_type"]; label: string; detail: string }[] = [
  { value: "parent", label: "I'm a parent or carer", detail: "Set up profiles for your children." },
  { value: "teacher", label: "I'm a teacher or tutor", detail: "Add a profile for each learner you support." },
  { value: "learner", label: "I'm learning myself", detail: "For teenagers and adults." },
];

export const AGE_BANDS = ["5-7", "8-10", "11-13", "14-17", "18+"];

export function RegisterPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [accountType, setAccountType] = useState<User["account_type"]>("parent");
  const [displayName, setDisplayName] = useState("");
  const [learnerName, setLearnerName] = useState("");
  const [ageBand, setAgeBand] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const forSomeoneElse = accountType !== "learner";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await api.register({
        email,
        password,
        display_name: displayName,
        account_type: accountType,
        learner_name: forSomeoneElse ? learnerName : undefined,
        learner_age_band: ageBand || undefined,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      });
      signIn(response);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Create an account" intro="It takes about a minute. You can add more learners later.">
      <form onSubmit={submit} className="stack">
        <fieldset className="choice-group">
          <legend>Who is this account for?</legend>
          {ACCOUNT_TYPES.map((type) => (
            <label key={type.value} className="choice">
              <input
                type="radio"
                name="account_type"
                value={type.value}
                checked={accountType === type.value}
                onChange={() => setAccountType(type.value)}
              />
              <span>
                <strong>{type.label}</strong>
                <span className="hint">{type.detail}</span>
              </span>
            </label>
          ))}
        </fieldset>

        <div className="field">
          <label htmlFor="display-name">Your name</label>
          <input id="display-name" value={displayName} onChange={(e) => setDisplayName(e.target.value)}
            autoComplete="name" required maxLength={80} />
        </div>

        {forSomeoneElse && (
          <div className="field">
            <label htmlFor="learner-name">Learner's first name or nickname</label>
            <input id="learner-name" value={learnerName} onChange={(e) => setLearnerName(e.target.value)}
              required maxLength={40} aria-describedby="learner-name-hint" />
            <p id="learner-name-hint" className="hint">
              We only ask for a first name. We never need a child's full name or birthday.
            </p>
          </div>
        )}

        <div className="field">
          <label htmlFor="age-band">{forSomeoneElse ? "Their age" : "Your age"} (optional)</label>
          <select id="age-band" value={ageBand} onChange={(e) => setAgeBand(e.target.value)}>
            <option value="">Prefer not to say</option>
            {AGE_BANDS.map((band) => (
              <option key={band} value={band}>
                {band}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            autoComplete="email" required />
        </div>
        <PasswordField value={password} onChange={setPassword} autoComplete="new-password"
          hint="At least 10 characters. A short sentence works well." />

        {error !== null && <ErrorNote error={error} />}
        <button type="submit" className="btn" disabled={busy}>
          {busy ? "Creating your account" : "Create account"}
        </button>
      </form>
      <p className="auth-switch">
        Already have an account? <Link to="/sign-in">Sign in</Link>
      </p>
    </AuthLayout>
  );
}

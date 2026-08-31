import { BrandMark } from "./Logo";
import { Eyebrow } from "./ui";

export function AuthLayout({ eyebrow, title, subtitle, children }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <aside className="flex items-end bg-[radial-gradient(circle_at_20%_20%,rgba(201,132,42,0.22),transparent_36%),linear-gradient(160deg,#0b3d4a_0%,#072c36_100%)] px-6 py-8 text-paper min-h-[34vh] lg:p-12">
        <div>
          <div className="mb-6">
            <BrandMark size="lg" inverted />
          </div>
          <h1 className="max-w-[14ch] text-4xl font-bold leading-tight lg:text-5xl">
            A calm harbor for customer conversations.
          </h1>
          <p className="mt-5 max-w-[36ch] leading-relaxed text-paper/80">
            Sign in to manage tickets, keep context in one place, and get people
            the answers they need.
          </p>
        </div>
      </aside>
      <main className="grid place-items-center p-8">
        <div className="w-full max-w-[420px]">
          <Eyebrow>{eyebrow}</Eyebrow>
          <h2 className="text-3xl font-bold">{title}</h2>
          <p className="mb-6 mt-2 leading-relaxed text-muted">{subtitle}</p>
          {children}
        </div>
      </main>
    </div>
  );
}

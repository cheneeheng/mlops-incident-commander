import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { USE_STUBS } from "@/lib/config";
import { EventStreamProvider } from "@/lib/events";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/incidents", label: "Incidents", end: false },
  { to: "/inject", label: "Inject", end: false },
  { to: "/approvals", label: "Approvals", end: false },
  { to: "/postmortems", label: "Postmortems", end: false },
  { to: "/costs", label: "Costs", end: false },
  { to: "/evals", label: "Evals", end: false },
];

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app">
      <aside className="sidebar">
        <h1>Incident Commander</h1>
        <nav className="nav">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="main">
        <header className="header">
          <strong>MLOps Incident Commander</strong>
          {USE_STUBS && <span className="badge medium">sample data</span>}
        </header>
        <main className="content">
          <EventStreamProvider>{children}</EventStreamProvider>
        </main>
      </div>
    </div>
  );
}

import { Route, Routes } from "react-router-dom";

import Layout from "@/components/Layout";
import Approvals from "@/pages/Approvals";
import Costs from "@/pages/Costs";
import Dashboard from "@/pages/Dashboard";
import Evals from "@/pages/Evals";
import IncidentDetail from "@/pages/IncidentDetail";
import Incidents from "@/pages/Incidents";
import Inject from "@/pages/Inject";
import Postmortems from "@/pages/Postmortems";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/incidents" element={<Incidents />} />
        <Route path="/incidents/:id" element={<IncidentDetail />} />
        <Route path="/inject" element={<Inject />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/postmortems" element={<Postmortems />} />
        <Route path="/costs" element={<Costs />} />
        <Route path="/evals" element={<Evals />} />
      </Routes>
    </Layout>
  );
}

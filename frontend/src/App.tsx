import React from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import { Protected } from "./components/Protected";
import Home, { Hackathons, HackathonDetail } from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Skills from "./pages/Skills";
import Team from "./pages/Team";
import ProjectsGallery, { ProjectDetail } from "./pages/Projects";
import { NewProject, ProjectEditor } from "./pages/ProjectEditor";
import { JudgeQueue, JudgeEvaluate, JudgeHistory } from "./pages/Judge";
import OrganizerHackathon from "./pages/OrganizerHackathon";
import OrganizerRubric from "./pages/OrganizerRubric";
import OrganizerJudges from "./pages/OrganizerJudges";
import OrganizerObservatory from "./pages/OrganizerObservatory";
import OrganizerRankings from "./pages/OrganizerRankings";
import OrganizerRankingLab from "./pages/OrganizerRankingLab";
import OrganizerAudit from "./pages/OrganizerAudit";
import AdminUsers from "./pages/AdminUsers";
import { useParams } from "react-router-dom";

function HackathonDetailRoute() {
  const { id } = useParams();
  return <HackathonDetail id={id!} />;
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/hackathons" element={<Hackathons />} />
        <Route path="/hackathons/:id" element={<HackathonDetailRoute />} />
        <Route path="/projects" element={<ProjectsGallery />} />
        <Route path="/projects/new" element={<Protected roles={["participant"]}><NewProject /></Protected>} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/projects/:id/edit" element={<Protected roles={["participant"]}><ProjectEditor /></Protected>} />

        <Route path="/dashboard" element={<Protected roles={["participant"]}><Dashboard /></Protected>} />
        <Route path="/skills" element={<Protected roles={["participant"]}><Skills /></Protected>} />
        <Route path="/team" element={<Protected roles={["participant"]}><Team /></Protected>} />

        <Route path="/judge" element={<Protected roles={["judge"]}><JudgeQueue /></Protected>} />
        <Route path="/judge/projects/:projectId" element={<Protected roles={["judge"]}><JudgeEvaluate /></Protected>} />
        <Route path="/judge/history" element={<Protected roles={["judge"]}><JudgeHistory /></Protected>} />

        <Route path="/organizer" element={<Protected roles={["organizer"]}><OrganizerHackathon /></Protected>} />
        <Route path="/organizer/rubric" element={<Protected roles={["organizer"]}><OrganizerRubric /></Protected>} />
        <Route path="/organizer/judges" element={<Protected roles={["organizer"]}><OrganizerJudges /></Protected>} />
        <Route path="/organizer/judging" element={<Protected roles={["organizer"]}><OrganizerObservatory /></Protected>} />
        <Route path="/organizer/rankings" element={<Protected roles={["organizer"]}><OrganizerRankings /></Protected>} />
        <Route path="/organizer/ranking-lab" element={<Protected roles={["organizer"]}><OrganizerRankingLab /></Protected>} />
        <Route path="/organizer/audit" element={<Protected roles={["organizer"]}><OrganizerAudit /></Protected>} />

        <Route path="/admin/users" element={<Protected roles={["admin"]}><AdminUsers /></Protected>} />
        <Route path="/admin/audit" element={<Protected roles={["admin"]}><OrganizerAudit /></Protected>} />

        <Route path="*" element={<p className="text-muted">Page not found.</p>} />
      </Routes>
    </Layout>
  );
}

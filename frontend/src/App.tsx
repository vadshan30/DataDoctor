import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { Dashboard } from "./pages/Dashboard";
import { DatasetDetails } from "./pages/DatasetDetails";
import { Datasets } from "./pages/Datasets";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";

function AuthenticatedLayout() {
	return <AppLayout><Outlet /></AppLayout>;
}

export default function App() {
	return (
		<Routes>
			<Route path="/login" element={<Login />} />
			<Route path="/register" element={<Register />} />
			<Route element={<ProtectedRoute />}>
				<Route element={<AuthenticatedLayout />}>
					<Route path="/dashboard" element={<Dashboard />} />
					<Route path="/datasets" element={<Datasets />} />
					<Route path="/datasets/:datasetId" element={<DatasetDetails />} />
					<Route path="/datasets/:datasetId/experiments" element={<DatasetDetails />} />
					<Route path="/datasets/:datasetId/reports" element={<DatasetDetails />} />
				</Route>
			</Route>
			<Route path="*" element={<Navigate to="/dashboard" replace />} />
		</Routes>
	);
}

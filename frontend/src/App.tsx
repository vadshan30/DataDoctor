import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { Dashboard } from "./components/Dashboard";
import { Home } from "./pages/Home";
import { DatasetDetails } from "./pages/DatasetDetails";
import { Datasets } from "./pages/Datasets";
import { Experiments } from "./pages/Experiments";
import { Reports } from "./pages/Reports";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { ForgotPassword } from "./pages/ForgotPassword";
import { ResetPassword } from "./pages/ResetPassword";
import "./index.css";

function AuthenticatedLayout() {
	return <Dashboard><Outlet /></Dashboard>;
}

export default function App() {
	return (
		<Routes>
			<Route path="/login" element={<Login />} />
			<Route path="/register" element={<Register />} />
			<Route path="/forgot-password" element={<ForgotPassword />} />
			<Route path="/reset-password" element={<ResetPassword />} />
			<Route element={<ProtectedRoute />}>
				<Route element={<AuthenticatedLayout />}>
					<Route path="/dashboard" element={<Home />} />
					<Route path="/datasets" element={<Datasets />} />
					<Route path="/experiments" element={<Experiments />} />
					<Route path="/reports" element={<Reports />} />
					<Route path="/datasets/:datasetId" element={<DatasetDetails />} />
					<Route path="/datasets/:datasetId/experiments" element={<DatasetDetails />} />
					<Route path="/datasets/:datasetId/reports" element={<DatasetDetails />} />
				</Route>
			</Route>
			<Route path="*" element={<Navigate to="/dashboard" replace />} />
		</Routes>
	);
}

import React from "react";
import {
    BrowserRouter,
    Routes,
    Route,
    Navigate,
} from "react-router-dom";

import DashboardLayout from "./layouts/DashboardLayout";
import Dashboard from "./pages/Dashboard";
import PatientRegistration from "./pages/PatientRegistration";

const App = () => {
    return (
        <BrowserRouter>
            <DashboardLayout>
                <Routes>
                    <Route
                        path="/"
                        element={<Navigate to="/dashboard" replace />}
                    />

                    <Route
                        path="/dashboard"
                        element={<Dashboard />}
                    />

                    <Route
                        path="/patient-registration"
                        element={<PatientRegistration />}
                    />
                </Routes>
            </DashboardLayout>
        </BrowserRouter>
    );
};

export default App;
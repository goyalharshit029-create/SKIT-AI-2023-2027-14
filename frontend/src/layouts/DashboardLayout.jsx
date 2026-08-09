import React from "react";
import Navbar from "../components/Navbar";
import Sidebar from "../components/Sidebar";

const DashboardLayout = ({ children }) => {
    return (
        <div className="app-container">
            <Navbar />

            <div className="main-container">
                <Sidebar />

                <main className="content">
                    {children}
                </main>
            </div>
        </div>
    );
};

export default DashboardLayout;
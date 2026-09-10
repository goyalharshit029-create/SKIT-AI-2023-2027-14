import React from "react";
import { NavLink } from "react-router-dom";

const Sidebar = () => {
    return (
        <aside className="sidebar">
            <div className="sidebar-title">
                <span>MAIN MENU</span>
            </div>

            <nav>
                <NavLink
                    to="/dashboard"
                    className={({ isActive }) =>
                        isActive ? "sidebar-link active" : "sidebar-link"
                    }
                >
                    <span>▣</span>
                    Dashboard
                </NavLink>

                <NavLink
                    to="/patient-registration"
                    className={({ isActive }) =>
                        isActive ? "sidebar-link active" : "sidebar-link"
                    }
                >
                    <span>＋</span>
                    New Patient
                </NavLink>
            </nav>

            <div className="sidebar-bottom">
                <div className="system-status">
                    <span className="status-dot"></span>

                    <div>
                        <strong>System Online</strong>
                        <small>AI services ready</small>
                    </div>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
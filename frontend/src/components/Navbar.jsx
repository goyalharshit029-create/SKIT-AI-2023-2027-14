import React from "react";

const Navbar = () => {
    return (
        <header className="navbar">
            <div className="navbar-left">
                <div className="logo-icon">♥</div>

                <div>
                    <h2>CVD-XAI</h2>
                    <span>Clinical Intelligence</span>
                </div>
            </div>

            <div className="navbar-right">
                <div className="notification">🔔</div>

                <div className="profile">
                    <div className="profile-avatar">DR</div>

                    <div>
                        <strong>Clinician</strong>
                        <span>Medical Professional</span>
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Navbar;
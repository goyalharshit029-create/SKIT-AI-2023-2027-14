import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const Dashboard = () => {
    const [patient, setPatient] = useState(null);

    useEffect(() => {
        const savedPatient = sessionStorage.getItem("cvd_xai_patient");

        if (savedPatient) {
            setPatient(JSON.parse(savedPatient));
        }
    }, []);

    return (
        <div className="page">
            <div className="page-header">
                <div>
                    <h1>Clinician Dashboard</h1>
                    <p>
                        Cardiovascular disease risk assessment and clinical insights.
                    </p>
                </div>
            </div>

            <div className="welcome-card">
                <div>
                    <span className="welcome-label">CVD-XAI</span>

                    <h2>Explainable Cardiovascular Risk Assessment</h2>

                    <p>
                        Review patient information, cardiovascular risk predictions,
                        ECG analysis and explainable AI insights from one dashboard.
                    </p>
                </div>

                <div className="heart-illustration">🫀</div>
            </div>

            <div className="dashboard-grid">
                <div className="dashboard-card">
                    <span className="card-icon">👥</span>

                    <div>
                        <span className="card-label">PATIENTS</span>
                        <h2>{patient ? "1" : "0"}</h2>
                        <p>Registered patients</p>
                    </div>
                </div>

                <div className="dashboard-card">
                    <span className="card-icon">🧠</span>

                    <div>
                        <span className="card-label">AI PREDICTIONS</span>
                        <h2>0</h2>
                        <p>Predictions generated</p>
                    </div>
                </div>

                <div className="dashboard-card">
                    <span className="card-icon">📊</span>

                    <div>
                        <span className="card-label">EXPLAINABILITY</span>
                        <h2>SHAP</h2>
                        <p>Feature-level insights</p>
                    </div>
                </div>
            </div>

            {patient ? (
                <div className="patient-summary">
                    <div className="patient-summary-header">
                        <div>
                            <span className="welcome-label">REGISTERED PATIENT</span>

                            <h2>{patient.name}</h2>

                            <p>Patient ID: {patient.patientId}</p>
                        </div>

                        <div className="patient-status">
                            <span className="status-dot"></span>
                            Registered
                        </div>
                    </div>

                    <div className="patient-details">
                        <div>
                            <span>AGE</span>
                            <strong>{patient.age}</strong>
                        </div>

                        <div>
                            <span>GENDER</span>
                            <strong>{patient.gender}</strong>
                        </div>

                        <div>
                            <span>BLOOD PRESSURE</span>
                            <strong>{patient.bloodPressure || "Not provided"}</strong>
                        </div>

                        <div>
                            <span>HEART RATE</span>
                            <strong>
                                {patient.heartRate
                                    ? `${patient.heartRate} BPM`
                                    : "Not provided"}
                            </strong>
                        </div>

                        <div>
                            <span>CHOLESTEROL</span>
                            <strong>
                                {patient.cholesterol
                                    ? `${patient.cholesterol} mg/dL`
                                    : "Not provided"}
                            </strong>
                        </div>

                        <div>
                            <span>DIABETES</span>
                            <strong>{patient.diabetes}</strong>
                        </div>
                    </div>

                    <div className="patient-actions">
                        <span>
                            AI prediction and ECG analysis will appear here after backend
                            integration.
                        </span>

                        <Link to="/patient-registration" className="secondary-btn">
                            Add Another Patient
                        </Link>
                    </div>
                </div>
            ) : (
                <div className="empty-state">
                    <div className="empty-icon">🩺</div>

                    <h2>No Patient Selected</h2>

                    <p>
                        Register a new patient to begin the cardiovascular risk
                        assessment workflow.
                    </p>

                    <Link to="/patient-registration" className="primary-btn empty-btn">
                        + Register New Patient
                    </Link>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
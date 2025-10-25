import React from "react";
import { useNavigate } from "react-router-dom";

const Dashboard = () => {
  const token = localStorage.getItem("access");
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    navigate("/"); // redirect back to login
  };

  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h2>Welcome to the Dashboard 🎉</h2>
      {token ? (
        <>
          <p>✅ You are logged in with JWT.</p>
          <button onClick={handleLogout}>Logout</button>
        </>
      ) : (
        <p>❌ No token found. Please login.</p>
      )}
    </div>
  );
};

export default Dashboard;

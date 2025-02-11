import React, { useState } from "react";
import "./styles.css";

export default function App() {
  const [mapHTML, setMapHTML] = useState("http://127.0.0.1:5000/maps/filtered_map.html");
  const [prompt, setPrompt] = useState("");

  const [loading, setLoading] = useState(false);

const handlePromptSubmit = async () => {
  setLoading(true); // Start loading
  try {
    const response = await fetch("http://127.0.0.1:5000/process-prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await response.json();

    const uniqueURL = `http://127.0.0.1:5000/maps/${data.filteredMap}?t=${new Date().getTime()}`;
    setMapHTML(uniqueURL);
  } catch (error) {
    console.error("Error fetching filtered map:", error);
  } finally {
    setLoading(false); // Stop loading
  }
};

return (
  <div className="container">
    <div className="map-container">
      {loading ? <p>Loading...</p> : <iframe src={mapHTML} className="map-iframe"></iframe>}
    </div>
    <div className="prompt-container">
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Enter a prompt, e.g., 'Show houses under 35k'"
      ></textarea>
      <button onClick={handlePromptSubmit} disabled={loading}>
        {loading ? "Loading..." : "Generate Filtered Map"}
      </button>
    </div>
  </div>
);


  return (
    <div className="container">
      <div className="map-container">
        <iframe src={mapHTML} className="map-iframe"></iframe>
      </div>
      <div className="prompt-container">
        <h1>Interactive Map Filter</h1>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter a prompt, e.g., 'Show houses under 35k'"
        ></textarea>
        <button onClick={handlePromptSubmit}>Generate Filtered Map</button>
      </div>
    </div>
  );
}

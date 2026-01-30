
import React from "react";
import SwaggerUI from "swagger-ui-react";
import "swagger-ui-react/swagger-ui.css";

export default function OpenApiTab() {
  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ fontWeight: 700, fontSize: 22, marginBottom: 12 }}>API & Agent Explorer</h2>
      <p style={{ fontSize: 15, marginBottom: 20 }}>
        Explore and test all backend APIs and agents. The OpenAPI (Swagger) UI below is live and interactive.
      </p>
      <SwaggerUI url="http://localhost:8000/openapi.json" docExpansion="list" />
      <div style={{ marginTop: 16, fontSize: 13, color: '#888' }}>
        <b>Tip:</b> If the API UI does not load, ensure the backend is running and accessible at <code>http://localhost:8000</code>.
      </div>
    </div>
  );
}

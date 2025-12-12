import { useEffect } from "react";
import {
  analyzePatient,
  getAdaptersStatus,
  getDashboardPatients,
  getDashboardSummary,
  getHealthStatus,
  queryMedical,
  submitFeedback,
} from "../api";

const HomePage = () => {
  useEffect(() => {
    const testApi = async () => {
      try {
        const health = await getHealthStatus();
        console.log("Health status", health);
      } catch (error) {
        console.error("Health status error", error);
      }

      try {
        const adapters = await getAdaptersStatus();
        console.log("Adapters status", adapters);
      } catch (error) {
        console.error("Adapters status error", error);
      }

      try {
        const patients = await getDashboardPatients();
        console.log("Dashboard patients", patients);
      } catch (error) {
        console.error("Dashboard patients error", error);
      }

      try {
        const summary = await getDashboardSummary();
        console.log("Dashboard summary", summary);
      } catch (error) {
        console.error("Dashboard summary error", error);
      }

      try {
        const analysis = await analyzePatient("demo-patient", {
          includeRecommendations: true,
          specialty: "cardiology",
        });
        console.log("Analysis result", analysis);
      } catch (error) {
        console.error("Analyze patient error", error);
      }

      try {
        const query = await queryMedical("What is the recommended follow-up?", {
          includeReasoning: true,
        });
        console.log("Query result", query);
      } catch (error) {
        console.error("Query error", error);
      }

      try {
        const feedback = await submitFeedback("query-id", "positive");
        console.log("Feedback response", feedback);
      } catch (error) {
        console.error("Feedback error", error);
      }
    };

    void testApi();
  }, []);

  return (
    <section className="page">
      <h1>Home (React)</h1>
    </section>
  );
};

export default HomePage;

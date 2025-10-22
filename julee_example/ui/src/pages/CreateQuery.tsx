"use client";

import { useNavigate } from "react-router-dom";
import QueryForm from "@/components/QueryForm";

export default function CreateQueryPage() {
  const navigate = useNavigate();

  const handleSuccess = (query: unknown) => {
    console.log("Query created successfully:", query);
    // Navigate back to queries page with success message
    navigate("/queries", {
      state: {
        success: `Query "${query.name}" created successfully!`,
      },
    });
  };

  const handleCancel = () => {
    navigate(-1); // Go back to previous page
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Create New Query
        </h1>
        <p className="text-muted-foreground">
          Define a new knowledge service query to extract specific information
          from documents
        </p>
      </div>

      <QueryForm onSuccess={handleSuccess} onCancel={handleCancel} />
    </div>
  );
}

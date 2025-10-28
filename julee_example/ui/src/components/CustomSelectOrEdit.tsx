"use client";

import { useState, useEffect } from "react";
import { PropertyEditor, getFormuleState } from "react-formule";
import FieldTypePicker from "./FieldTypePicker";

export default function CustomSelectOrEdit() {
  const [selectedFieldPath, setSelectedFieldPath] = useState<string | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);

  // Monitor formule state to determine if a field is selected for editing
  useEffect(() => {
    const updateState = () => {
      try {
        const state = getFormuleState();

        // Check if there's a selected field path in the wizard state
        const fieldPath = (state as any)?.schemaWizard?.field || null;
        setSelectedFieldPath(fieldPath);
        setIsLoading(false);
      } catch (err) {
        console.warn("Could not get formule state:", err);
        setIsLoading(false);
      }
    };

    updateState();

    // Set up interval to check state changes
    const interval = setInterval(updateState, 100);

    return () => clearInterval(interval);
  }, []);

  // Show loading state while we determine the current mode
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-current"></div>
      </div>
    );
  }

  // If a field is selected, show the property editor
  if (selectedFieldPath) {
    return <PropertyEditor />;
  }

  // If no field is selected, show our custom field type picker
  return <FieldTypePicker />;
}

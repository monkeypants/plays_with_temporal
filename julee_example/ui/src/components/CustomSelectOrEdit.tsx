"use client";

import { useState, useEffect } from "react";
import { SelectOrEdit, PropertyEditor, getFormuleState } from "react-formule";
import FieldTypePicker from "./FieldTypePicker";

export default function CustomSelectOrEdit() {
  const [selectedFieldPath, setSelectedFieldPath] = useState<string | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  // Error boundary effect to catch react-formule errors
  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      if (event.message.includes("can't access property Symbol.iterator")) {
        console.warn("React-formule navigation error caught, resetting state");
        setHasError(true);
        setSelectedFieldPath(null);
        // Reset error after a short delay
        setTimeout(() => setHasError(false), 100);
        event.preventDefault();
      }
    };

    window.addEventListener("error", handleError);
    return () => window.removeEventListener("error", handleError);
  }, []);

  // Monitor formule state to determine if a field is selected for editing
  useEffect(() => {
    const updateState = () => {
      try {
        const state = getFormuleState();

        // Check multiple possible paths for selected field
        const fieldPath =
          (state as any)?.schemaWizard?.field || (state as any)?.field || null;

        // Also check if there's any non-empty field selection
        const hasSelectedField =
          fieldPath &&
          (typeof fieldPath === "string"
            ? fieldPath.trim() !== ""
            : typeof fieldPath === "object"
              ? Object.keys(fieldPath).length > 0
              : Boolean(fieldPath));

        const newSelectedPath = hasSelectedField ? fieldPath : null;

        // Only update state if it actually changed to avoid unnecessary re-renders
        if (
          JSON.stringify(newSelectedPath) !== JSON.stringify(selectedFieldPath)
        ) {
          setSelectedFieldPath(newSelectedPath);
        }
        setIsLoading(false);
      } catch (err) {
        console.warn("Could not get formule state:", err);
        setSelectedFieldPath(null);
        setIsLoading(false);
      }
    };

    updateState();

    // Set up interval to check state changes
    const interval = setInterval(updateState, 200);

    return () => clearInterval(interval);
  }, [selectedFieldPath]);

  // Show loading state while we determine the current mode
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-current"></div>
      </div>
    );
  }

  // If there's an error, force show field picker
  if (hasError) {
    return <FieldTypePicker />;
  }

  // If a field is selected, show the property editor wrapped in error boundary
  if (selectedFieldPath) {
    try {
      return <PropertyEditor />;
    } catch (err) {
      console.warn("PropertyEditor error, falling back to field picker:", err);
      setSelectedFieldPath(null);
      return <FieldTypePicker />;
    }
  }

  // If no field is selected, show our custom field type picker
  return <FieldTypePicker />;
}

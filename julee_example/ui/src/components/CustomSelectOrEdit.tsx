"use client";

import React from "react";
import { useSelector } from "react-redux";
import { isEmpty } from "lodash-es";
import FieldTypePicker from "./FieldTypePicker";
import CustomPropertyEditor from "./CustomPropertyEditor";

interface CustomSelectOrEditProps {
  knowledgeServiceQueries?: Record<string, string>;
  onUpdateQuery?: (jsonPointer: string, queryId: string | null) => void;
}

export default function CustomSelectOrEdit({
  knowledgeServiceQueries = {},
  onUpdateQuery,
}: CustomSelectOrEditProps) {
  // Use Redux selector to watch for field selection changes (same as original SelectOrEdit)
  const selectedField = useSelector((state: any) => state.schemaWizard.field);

  // Error boundary to catch react-formule navigation errors
  const [hasError, setHasError] = React.useState(false);

  React.useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      const errorObj = event.error;
      if (
        errorObj instanceof TypeError ||
        (errorObj && errorObj.name === "TypeError")
      ) {
        console.warn(
          "React-formule navigation TypeError caught, resetting state",
          errorObj,
        );
        setHasError(true);
        // Reset error after a short delay
        setTimeout(() => setHasError(false), 100);
        event.preventDefault();
      }
    };

    window.addEventListener("error", handleError);
    return () => window.removeEventListener("error", handleError);
  }, []);

  // If there's an error, force show field picker
  if (hasError) {
    return <FieldTypePicker />;
  }

  // If a field is selected (not empty), show CustomPropertyEditor, otherwise show our custom picker
  // This mirrors the logic from the original SelectOrEdit component
  return isEmpty(selectedField) ? (
    <FieldTypePicker />
  ) : (
    <CustomPropertyEditor
      knowledgeServiceQueries={knowledgeServiceQueries}
      onUpdateQuery={onUpdateQuery}
    />
  );
}

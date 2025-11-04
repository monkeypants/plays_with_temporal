"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useSelector, useDispatch } from "react-redux";
import { get } from "lodash-es";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Trash2, Edit3 } from "lucide-react";
import KnowledgeServiceSection from "./KnowledgeServiceSection";

interface CustomPropertyEditorProps {
  knowledgeServiceQueries?: Record<string, string>;
  onUpdateQuery?: (jsonPointer: string, queryId: string | null) => void;
}

const CustomPropertyEditor = ({
  knowledgeServiceQueries = {},
  onUpdateQuery,
}: CustomPropertyEditorProps) => {
  const [fieldName, setFieldName] = useState<string>("");
  const [localFieldName, setLocalFieldName] = useState<string>("");
  const fieldNameInputRef = React.useRef<HTMLInputElement>(null);
  const dispatch = useDispatch();

  // Get field information from Redux state
  const path = useSelector(
    (state: unknown) => (state as any).schemaWizard.field.path,
  );
  const uiPath = useSelector(
    (state: unknown) => (state as any).schemaWizard.field.uiPath,
  );

  const schema = useSelector((state: unknown) =>
    get((state as any).schemaWizard, ["current", "schema", ...path]),
  );

  // Get field title from schema
  const fieldTitle = schema?.title || "";

  // Determine field type and name
  const computedFieldName = useMemo(() => {
    if (path && path.length > 0) {
      const name = path.findLast(
        (item: string) => item !== "properties" && item !== "items",
      );
      return name || "root";
    }
    return "root";
  }, [path]);

  // Update field names when computed name changes
  useEffect(() => {
    setFieldName(computedFieldName);
    setLocalFieldName(computedFieldName);
  }, [computedFieldName]);

  // Create breadcrumb display
  const renderBreadcrumb = () => {
    if (!path || path.length === 0) return "Root";

    const breadcrumbParts = [];
    let currentName = "";

    for (const item of path) {
      if (item === "properties") {
        breadcrumbParts.push(`{ } ${currentName}`.trim());
        currentName = "";
      } else if (item === "items") {
        breadcrumbParts.push(`[ ] ${currentName}`.trim());
        currentName = "";
      } else {
        currentName = item;
      }
    }

    if (currentName) {
      breadcrumbParts.push(currentName);
    }

    return breadcrumbParts.join(" → ");
  };

  const handleBack = () => {
    dispatch({ type: "schemaWizard/enableCreateMode" });
  };

  const handleDelete = () => {
    if (path && path.length > 0) {
      dispatch({
        type: "schemaWizard/deleteByPath",
        payload: { path: { path, uiPath } },
      });
      dispatch({ type: "schemaWizard/enableCreateMode" });
    }
  };

  const handleRename = (newName: string) => {
    if (newName && newName !== fieldName) {
      dispatch({
        type: "schemaWizard/renameIdByPath",
        payload: {
          path: { path, uiPath },
          newName,
          separator: "::", // Default separator used by react-formule
        },
      });
      setFieldName(newName);
    }
  };

  const handleFieldNameBlur = () => {
    if (localFieldName && localFieldName !== fieldName) {
      handleRename(localFieldName);
    }
  };

  const handleTitleChange = useCallback(
    (newTitle: string) => {
      if (!path) return;

      dispatch({
        type: "schemaWizard/updateSchemaByPath",
        payload: {
          path: [...path, "title"],
          value: newTitle,
        },
      });
    },
    [dispatch, path],
  );

  const handleDescriptionChange = useCallback(
    (newDescription: string) => {
      if (!path) return;

      dispatch({
        type: "schemaWizard/updateSchemaByPath",
        payload: {
          path: [...path, "description"],
          value: newDescription,
        },
      });
    },
    [dispatch, path],
  );

  return (
    <div className="flex flex-col h-full w-full">
      {/* Header */}
      <div className="border-b pb-4 mb-4">
        <div className="flex items-center justify-between mb-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>

          {path && path.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDelete}
              className="flex items-center gap-2 text-red-600 hover:text-red-700"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </Button>
          )}
        </div>

        <div className="text-center">
          {path && path.length > 0 ? (
            <div className="flex items-center justify-center gap-2">
              <input
                ref={fieldNameInputRef}
                type="text"
                value={localFieldName}
                onChange={(e) => setLocalFieldName(e.target.value)}
                onBlur={handleFieldNameBlur}
                className="text-lg font-semibold bg-transparent border-none text-center outline-none focus:bg-white focus:border focus:border-blue-500 focus:rounded px-2 py-1"
                placeholder="Field name"
              />
              <Edit3
                className="h-4 w-4 text-gray-400 cursor-pointer hover:text-gray-600"
                onClick={() => fieldNameInputRef.current?.focus()}
              />
            </div>
          ) : (
            <h2 className="text-lg font-semibold">{fieldName}</h2>
          )}
          <p className="text-sm text-muted-foreground">{renderBreadcrumb()}</p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 space-y-4 w-full">
        <Card className="w-full">
          <CardHeader>
            <CardTitle className="text-base">Field Properties</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Field Type</label>
              <p className="text-sm text-muted-foreground mt-1">
                {schema?.type || "Unknown"}
              </p>
            </div>

            <div>
              <label className="text-sm font-medium">Title</label>
              <input
                type="text"
                value={fieldTitle}
                onChange={(e) => handleTitleChange(e.target.value)}
                className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
                placeholder="Enter field title"
              />
            </div>

            <div>
              <label className="text-sm font-medium">Description</label>
              <textarea
                className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
                rows={3}
                placeholder="Add a description for this field"
                value={schema?.description || ""}
                onChange={(e) => handleDescriptionChange(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Knowledge Service Section */}
        <KnowledgeServiceSection
          knowledgeServiceQueries={knowledgeServiceQueries}
          onUpdateQuery={onUpdateQuery}
        />
      </div>
    </div>
  );
};

export default CustomPropertyEditor;

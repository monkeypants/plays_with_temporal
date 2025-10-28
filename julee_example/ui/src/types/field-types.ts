import { ReactNode } from "react";

export interface FieldType {
  id: string;
  title: string;
  description: string;
  icon: ReactNode;
  category: "collections" | "simple";
  schema: {
    type: string;
    properties?: Record<string, unknown>;
    items?: Record<string, unknown>;
  };
  uiSchema: Record<string, unknown>;
}

export interface FieldTypeCategory {
  title: string;
  fields: FieldType[];
}

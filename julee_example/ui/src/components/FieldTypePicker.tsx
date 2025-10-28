"use client";

import React from "react";
import { DndProvider, useDrag } from "react-dnd";
import { MultiBackend } from "react-dnd-multi-backend";
import { HTML5toTouch } from "rdndmb-html5-to-touch";
import { Card, CardContent } from "@/components/ui/card";

import { Braces, List, Type, Hash } from "lucide-react";

interface FieldTypeData {
  title: string;
  icon: React.ReactNode;
  description: string;
  child: Record<string, unknown>;
  default: {
    schema: Record<string, unknown>;
    uiSchema: Record<string, unknown>;
  };
}

// Our 4 field types with complete data definitions
const FIELD_TYPES: Record<string, FieldTypeData> = {
  object: {
    title: "Object",
    icon: <Braces className="h-4 w-4" />,
    description: "Group of fields, useful for nesting",
    child: {},
    default: {
      schema: {
        type: "object",
        properties: {},
      },
      uiSchema: {},
    },
  },
  array: {
    title: "List",
    icon: <List className="h-4 w-4" />,
    description: "List of fields supporting addition, deletion and reordering",
    child: {},
    default: {
      schema: {
        type: "array",
        items: {},
      },
      uiSchema: {},
    },
  },
  text: {
    title: "Text",
    icon: <Type className="h-4 w-4" />,
    description: "Text field supporting validation",
    child: {},
    default: {
      schema: {
        type: "string",
      },
      uiSchema: {
        "ui:widget": "text",
      },
    },
  },
  number: {
    title: "Number",
    icon: <Hash className="h-4 w-4" />,
    description: "Number field (integer or float)",
    child: {},
    default: {
      schema: {
        type: "number",
      },
      uiSchema: {},
    },
  },
};

interface DraggableFieldCardProps {
  fieldKey: string;
  fieldData: FieldTypeData;
}

const DraggableFieldCard: React.FC<DraggableFieldCardProps> = ({
  fieldKey,
  fieldData,
}) => {
  const [{ isDragging }, drag] = useDrag({
    type: "FIELD_TYPE", // Use the same type as react-formule
    item: { data: fieldData },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const opacity = isDragging ? 0.4 : 1;

  return (
    <div
      ref={drag}
      style={{ opacity }}
      data-cy={`field-${fieldKey}`} // Add data-cy for compatibility
    >
      <Card className="cursor-move transition-all hover:shadow-md hover:bg-accent/50 border-2 hover:border-primary/20">
        <CardContent className="p-4">
          <div className="flex items-start space-x-3">
            <div className="shrink-0 mt-1 text-primary">{fieldData.icon}</div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-foreground mb-1">
                {fieldData.title}
              </h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {fieldData.description}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const FieldTypePickerContent: React.FC = () => {
  return (
    <div className="grid gap-3">
      {Object.entries(FIELD_TYPES).map(([key, data]) => (
        <DraggableFieldCard key={key} fieldKey={key} fieldData={data} />
      ))}
    </div>
  );
};

export default function FieldTypePicker() {
  return (
    <DndProvider backend={MultiBackend} options={HTML5toTouch} context={window}>
      <FieldTypePickerContent />
    </DndProvider>
  );
}

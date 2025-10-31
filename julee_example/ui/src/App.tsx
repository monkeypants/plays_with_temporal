import { Routes, Route } from "react-router-dom";
import { Suspense } from "react";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Queries from "./pages/Queries";
import CreateQuery from "./pages/CreateQuery";
import QueryDetail from "./pages/QueryDetail";
import Specifications from "./pages/Specifications";
import CreateAssemblySpecification from "./pages/CreateAssemblySpecification";
import AssemblySpecificationDetail from "./pages/AssemblySpecificationDetail";
import NotFound from "./pages/NotFound";
import { Skeleton } from "./components/ui/skeleton";

// Loading fallback component
const LoadingFallback = () => (
  <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-96" />
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="rounded-lg border p-6 space-y-4">
            <div className="flex items-center justify-between">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-4" />
            </div>
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-3 w-24" />
          </div>
        ))}
      </div>
    </div>
  </div>
);

function App() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Layout>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/queries" element={<Queries />} />
            <Route path="/queries/create" element={<CreateQuery />} />
            <Route path="/queries/:queryId" element={<QueryDetail />} />
            <Route path="/specifications" element={<Specifications />} />
            <Route
              path="/specifications/create"
              element={<CreateAssemblySpecification />}
            />
            <Route
              path="/specifications/:specificationId"
              element={<AssemblySpecificationDetail />}
            />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </Layout>
    </div>
  );
}

export default App;

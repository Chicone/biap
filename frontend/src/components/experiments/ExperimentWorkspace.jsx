import { useState } from "react";
import OverviewTab from "./OverviewTab";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import DatasetsTab from "./DatasetsTab";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

function ExperimentWorkspace({ experiment, onBack, initialTab = "overview" }) {
  const [activeTab, setActiveTab] = useState(initialTab);
  const [activeDataset, setActiveDataset] = useState(null);

  return (
    <Card className="experiment-workspace">
      <CardHeader>
        <Button variant="secondary" className="back-button" onClick={onBack}>
          ← Back to Experiments
        </Button>

        <div className="workspace-header">
          <div>
            <CardTitle>{experiment.name}</CardTitle>
            <CardDescription>
              {experiment.description || "No description provided."}
            </CardDescription>
          </div>

          <Badge>{experiment.status}</Badge>
        </div>
      </CardHeader>

      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="datasets">Datasets</TabsTrigger>
            <TabsTrigger value="models">Models</TabsTrigger>
            <TabsTrigger value="results">Results</TabsTrigger>
            <TabsTrigger value="reports">Reports</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <OverviewTab experiment={experiment} />
          </TabsContent>

          <TabsContent value="datasets">
            <DatasetsTab
              experimentId={experiment.id}
              activeDataset={activeDataset}
              onSelectDataset={setActiveDataset}
            />
          </TabsContent>

          <TabsContent value="models">
            <p>Model workspace coming soon.</p>
          </TabsContent>

          <TabsContent value="results">
            <p>Results dashboard coming soon.</p>
          </TabsContent>

          <TabsContent value="reports">
            <p>Scientific reports coming soon.</p>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

export default ExperimentWorkspace;
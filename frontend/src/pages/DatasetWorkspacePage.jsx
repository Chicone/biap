import { useNavigate, useParams } from "react-router-dom";
import ImagesTab from "@/components/experiments/ImagesTab";
import FeatureAnalysisTab from "@/components/experiments/FeatureAnalysisTab";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

function DatasetWorkspacePage() {
  const { experimentId, datasetId } = useParams();
  const navigate = useNavigate();

  const activeDataset = {
    id: Number(datasetId),
  };

  return (
    <section className="panel">
      <button
        className="secondary-button"
        onClick={() => navigate(`/experiments/${experimentId}?tab=datasets`)}
      >
        ← Back to Experiment
      </button>

    <Card>
      <CardHeader>
        <CardTitle>Dataset {datasetId}</CardTitle>
        <CardDescription>
          Browse images, create annotations and preprocess data.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <Tabs defaultValue="images">
          <TabsList>
            <TabsTrigger value="images">Images</TabsTrigger>
            <TabsTrigger value="annotations">Annotations</TabsTrigger>
            <TabsTrigger value="preprocessing">Preprocessing</TabsTrigger>
            <TabsTrigger value="feature-analysis">Feature Analysis</TabsTrigger>
            <TabsTrigger value="statistics">Statistics</TabsTrigger>
          </TabsList>

          <TabsContent value="images">
            <ImagesTab activeDataset={activeDataset} />
          </TabsContent>

          <TabsContent value="annotations">
            Annotation workspace coming soon.
          </TabsContent>

          <TabsContent value="preprocessing">
            Preprocessing workspace coming soon.
          </TabsContent>

          <TabsContent value="feature-analysis">
            <FeatureAnalysisTab activeDataset={activeDataset} />
          </TabsContent>

          <TabsContent value="statistics">
            Dataset statistics coming soon.
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
    </section>
  );
}

export default DatasetWorkspacePage;
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import ImagesTab from "@/components/experiments/ImagesTab";
import FeatureAnalysisTab from "@/components/experiments/FeatureAnalysisTab";
import MachineLearningTab from "@/components/experiments/MachineLearningTab";

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

import AntibodySamplesTab from "@/components/experiments/AntibodySamplesTab";

const API_URL = "http://127.0.0.1:8002";

function DatasetWorkspacePage() {
  const { experimentId, datasetId } = useParams();
  const navigate = useNavigate();

  const [activeDataset, setActiveDataset] = useState(null);
  const [datasetError, setDatasetError] = useState(null);

  useEffect(() => {
    async function loadDataset() {
      setDatasetError(null);
      setActiveDataset(null);

      try {
        const response = await fetch(
          `${API_URL}/datasets/${datasetId}`
        );

        if (!response.ok) {
          throw new Error("Failed to load dataset");
        }

        const dataset = await response.json();
        setActiveDataset(dataset);
      } catch (error) {
        setDatasetError(error.message);
      }
    }

    loadDataset();
  }, [datasetId]);

  if (datasetError) {
    return (
      <section className="panel">
        <p>{datasetError}</p>
      </section>
    );
  }

  if (!activeDataset) {
    return (
      <section className="panel">
        <p>Loading dataset...</p>
      </section>
    );
  }

  const isAntibodyDataset =
    activeDataset.dataset_type?.toLowerCase() === "antibody";

  return (
    <section className="panel">
      <button
        className="secondary-button"
        onClick={() =>
          navigate(`/experiments/${experimentId}?tab=datasets`)
        }
      >
        ← Back to Experiment
      </button>

      <Card>
        <CardHeader>
          <CardTitle>{activeDataset.name}</CardTitle>

        <CardDescription>
          {isAntibodyDataset
            ? "Antibody dataset · Browse samples, build features and train models."
            : `${activeDataset.dataset_type} dataset · Browse images, create annotations, preprocess data and train models.`}
        </CardDescription>
        </CardHeader>

        <CardContent>
          <Tabs defaultValue={isAntibodyDataset ? "samples" : "images"}>
            <TabsList>
              {isAntibodyDataset ? (
                <TabsTrigger value="samples">
                  Samples
                </TabsTrigger>
              ) : (
                <>
                  <TabsTrigger value="images">
                    Images
                  </TabsTrigger>

                  <TabsTrigger value="annotations">
                    Annotations
                  </TabsTrigger>

                  <TabsTrigger value="preprocessing">
                    Preprocessing
                  </TabsTrigger>
                </>
              )}
              <TabsTrigger value="feature-analysis">
                Feature Analysis
              </TabsTrigger>
              <TabsTrigger value="machine-learning">
                Machine Learning
              </TabsTrigger>
              <TabsTrigger value="statistics">
                Statistics
              </TabsTrigger>
            </TabsList>

            {isAntibodyDataset ? (
              <TabsContent value="samples">
                <AntibodySamplesTab activeDataset={activeDataset} />
              </TabsContent>
            ) : (
              <>
                <TabsContent value="images">
                  <ImagesTab activeDataset={activeDataset} />
                </TabsContent>

                <TabsContent value="annotations">
                  Annotation workspace coming soon.
                </TabsContent>

                <TabsContent value="preprocessing">
                  Preprocessing workspace coming soon.
                </TabsContent>
              </>
            )}

            <TabsContent value="feature-analysis">
              <FeatureAnalysisTab activeDataset={activeDataset} />
            </TabsContent>

            <TabsContent value="machine-learning">
              <MachineLearningTab activeDataset={activeDataset} />
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
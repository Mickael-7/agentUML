import { ShieldCheck, FileCheck, Sparkles } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { QualityPanel } from "@/components/quality/QualityPanel";
import { UseCaseEvalPanel } from "@/components/quality/UseCaseEvalPanel";
import { FullAnalysisPanel } from "@/components/quality/FullAnalysisPanel";

export function QualityView() {
  return (
    <Tabs defaultValue="requirements" className="flex h-full w-full flex-col">
      <div className="flex items-center gap-1 border-b border-border px-4 pt-2">
        <TabsList>
          <TabsTrigger value="requirements" className="gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5" />
            Requisitos
          </TabsTrigger>
          <TabsTrigger value="usecases" className="gap-1.5">
            <FileCheck className="h-3.5 w-3.5" />
            Casos de Uso
          </TabsTrigger>
          <TabsTrigger value="full" className="gap-1.5">
            <Sparkles className="h-3.5 w-3.5" />
            Análise Completa
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="requirements" className="mt-0 flex-1 overflow-hidden">
        <QualityPanel />
      </TabsContent>
      <TabsContent value="usecases" className="mt-0 flex-1 overflow-hidden">
        <UseCaseEvalPanel />
      </TabsContent>
      <TabsContent value="full" className="mt-0 flex-1 overflow-hidden">
        <FullAnalysisPanel />
      </TabsContent>
    </Tabs>
  );
}

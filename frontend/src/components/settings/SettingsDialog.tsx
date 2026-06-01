import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { useConfig } from "@/hooks/useConfig";

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onProviderChange?: (provider: string) => void;
  onModelChange?: (model: string) => void;
}

export function SettingsDialog({ open, onOpenChange, onProviderChange, onModelChange }: SettingsDialogProps) {
  const { config, saveConfig } = useConfig();
  const [provider, setProvider] = useState(config?.provider || "");
  const [model, setModel] = useState(config?.model || "");

  useEffect(() => {
    if (config) {
      setProvider(config.provider);
      setModel(config.model);
    }
  }, [config]);

  const models = config?.provider_models[provider] || [];

  const handleSave = async () => {
    await saveConfig({ provider, model });
    onProviderChange?.(provider);
    onModelChange?.(model);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Configuracoes</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Provider LLM</label>
            <Select value={provider} onValueChange={(v) => { setProvider(v); setModel(""); }}>
              <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
              <SelectContent>
                {config?.available_providers.map((p) => (
                  <SelectItem key={p} value={p}>{p}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Modelo</label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m} value={m}>{m}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={handleSave} className="w-full">Salvar</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

"use client";

import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { isUsingLocalAI } from "@/lib/fal";

import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { Input } from "./ui/input";
import { Cpu, Cloud, CheckCircle2, XCircle, Loader2 } from "lucide-react";

type KeyDialogProps = {} & Parameters<typeof Dialog>[0];

type ServiceHealth = {
  status: "checking" | "healthy" | "unhealthy" | "unreachable";
  url?: string;
};

type LocalAIHealth = {
  gateway: ServiceHealth;
  services: {
    comfyui: ServiceHealth;
    cosmos: ServiceHealth;
    audiocraft: ServiceHealth;
    tts: ServiceHealth;
  };
};

export function KeyDialog({ onOpenChange, open, ...props }: KeyDialogProps) {
  const [falKey, setFalKey] = useState("");
  const [localHealth, setLocalHealth] = useState<LocalAIHealth | null>(null);
  const [checkingHealth, setCheckingHealth] = useState(false);

  const localGatewayUrl =
    process.env.NEXT_PUBLIC_LOCAL_AI_URL || "http://localhost:10000";

  const handleOnOpenChange = (isOpen: boolean) => {
    onOpenChange?.(isOpen);
  };

  const handleSave = () => {
    localStorage.setItem("falKey", falKey);
    handleOnOpenChange(false);
    setFalKey("");
  };

  // Check local AI health when dialog opens and we're in local mode
  useEffect(() => {
    if (open && isUsingLocalAI) {
      checkLocalHealth();
    }
  }, [open]);

  const checkLocalHealth = async () => {
    setCheckingHealth(true);
    try {
      const response = await fetch(`${localGatewayUrl}/health/detailed`, {
        signal: AbortSignal.timeout(5000),
      });

      if (response.ok) {
        const data = await response.json();
        setLocalHealth({
          gateway: { status: "healthy", url: localGatewayUrl },
          services: {
            comfyui: {
              status: data.services?.comfyui?.status === "healthy" ? "healthy" : "unhealthy",
              url: data.services?.comfyui?.url,
            },
            cosmos: {
              status: data.services?.cosmos?.status === "healthy" ? "healthy" : "unhealthy",
              url: data.services?.cosmos?.url,
            },
            audiocraft: {
              status: data.services?.audiocraft?.status === "healthy" ? "healthy" : "unhealthy",
              url: data.services?.audiocraft?.url,
            },
            tts: {
              status: data.services?.tts?.status === "healthy" ? "healthy" : "unhealthy",
              url: data.services?.tts?.url,
            },
          },
        });
      } else {
        setLocalHealth({
          gateway: { status: "unhealthy", url: localGatewayUrl },
          services: {
            comfyui: { status: "unreachable" },
            cosmos: { status: "unreachable" },
            audiocraft: { status: "unreachable" },
            tts: { status: "unreachable" },
          },
        });
      }
    } catch (error) {
      setLocalHealth({
        gateway: { status: "unreachable", url: localGatewayUrl },
        services: {
          comfyui: { status: "unreachable" },
          cosmos: { status: "unreachable" },
          audiocraft: { status: "unreachable" },
          tts: { status: "unreachable" },
        },
      });
    }
    setCheckingHealth(false);
  };

  const StatusIcon = ({ status }: { status: ServiceHealth["status"] }) => {
    switch (status) {
      case "checking":
        return <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />;
      case "healthy":
        return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
      case "unhealthy":
        return <XCircle className="w-4 h-4 text-amber-500" />;
      case "unreachable":
        return <XCircle className="w-4 h-4 text-red-500" />;
    }
  };

  const serviceLabels: Record<string, { name: string; description: string }> = {
    comfyui: { name: "ComfyUI", description: "Image generation (Flux.1-dev)" },
    cosmos: { name: "Cosmos", description: "Video generation" },
    audiocraft: { name: "Audiocraft", description: "Music generation (MusicGen)" },
    tts: { name: "Kokoro TTS", description: "Text-to-speech" },
  };

  return (
    <Dialog {...props} onOpenChange={handleOnOpenChange} open={open}>
      <DialogContent className="flex flex-col max-w-lg h-fit">
        <DialogHeader>
          <DialogTitle className="sr-only">Settings</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col flex-1 gap-6">
          {/* Mode indicator */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Settings</h2>
            {isUsingLocalAI ? (
              <Badge
                variant="outline"
                className="gap-1.5 bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
              >
                <Cpu className="w-3 h-3" />
                Local AI Mode
              </Badge>
            ) : (
              <Badge
                variant="outline"
                className="gap-1.5 bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400"
              >
                <Cloud className="w-3 h-3" />
                Cloud Mode
              </Badge>
            )}
          </div>

          {isUsingLocalAI ? (
            /* Local AI settings */
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Gateway URL</span>
                <code className="text-xs bg-muted px-2 py-1 rounded">
                  {localGatewayUrl}
                </code>
              </div>

              <div className="border rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">Local Services</h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={checkLocalHealth}
                    disabled={checkingHealth}
                  >
                    {checkingHealth ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      "Refresh"
                    )}
                  </Button>
                </div>

                {localHealth ? (
                  <div className="space-y-2">
                    {(Object.keys(serviceLabels) as Array<keyof typeof serviceLabels>).map(
                      (key) => (
                        <div
                          key={key}
                          className="flex items-center justify-between py-1"
                        >
                          <div className="flex flex-col">
                            <span className="text-sm">{serviceLabels[key].name}</span>
                            <span className="text-xs text-muted-foreground">
                              {serviceLabels[key].description}
                            </span>
                          </div>
                          <StatusIcon
                            status={
                              localHealth.services[key as keyof typeof localHealth.services]
                                ?.status || "unreachable"
                            }
                          />
                        </div>
                      )
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Click Refresh to check service status
                  </p>
                )}
              </div>

              <p className="text-xs text-muted-foreground">
                Local AI mode uses on-device inference. Set{" "}
                <code className="bg-muted px-1 rounded">NEXT_PUBLIC_LOCAL_AI=false</code>{" "}
                to switch to cloud mode.
              </p>
            </div>
          ) : (
            /* Cloud settings - FAL Key */
            <div className="flex flex-col gap-4">
              <h3 className="text-sm font-medium">FAL API Key</h3>
              <Input
                placeholder="Your FAL Key"
                value={falKey}
                onChange={(e) => setFalKey(e.target.value)}
              />
              <div className="flex-1 flex flex-row items-end justify-center gap-2">
                <Button onClick={handleSave}>Save</Button>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          {!isUsingLocalAI && (
            <p className="text-muted-foreground text-sm mt-4 w-full text-center">
              You can get your FAL Key from{" "}
              <a
                className="underline underline-offset-2 decoration-foreground/50 text-foreground"
                href="https://fal.ai/dashboard/keys"
              >
                here
              </a>
              .
            </p>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

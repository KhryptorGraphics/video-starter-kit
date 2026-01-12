"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Logo } from "./logo";
import { SettingsIcon, Cpu, Cloud } from "lucide-react";
import { isUsingLocalAI } from "@/lib/fal";

export default function Header({
  openKeyDialog,
}: {
  openKeyDialog?: () => void;
}) {
  const localGatewayUrl =
    process.env.NEXT_PUBLIC_LOCAL_AI_URL || "http://localhost:10000";

  return (
    <header className="px-4 py-2 flex justify-between items-center border-b border-border">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-medium">
          <Logo />
        </h1>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              {isUsingLocalAI ? (
                <Badge
                  variant="outline"
                  className="gap-1.5 bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
                >
                  <Cpu className="w-3 h-3" />
                  Local AI
                </Badge>
              ) : (
                <Badge
                  variant="outline"
                  className="gap-1.5 bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400"
                >
                  <Cloud className="w-3 h-3" />
                  Cloud
                </Badge>
              )}
            </TooltipTrigger>
            <TooltipContent>
              {isUsingLocalAI ? (
                <p>
                  Using local AI at{" "}
                  <code className="text-xs bg-muted px-1 py-0.5 rounded">
                    {localGatewayUrl}
                  </code>
                </p>
              ) : (
                <p>Using fal.ai cloud services</p>
              )}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <nav className="flex flex-row items-center justify-end gap-1">
        <Button variant="ghost" size="sm" asChild>
          <a href="https://fal.ai" target="_blank" rel="noopener noreferrer">
            fal.ai
          </a>
        </Button>
        <Button variant="ghost" size="sm" asChild>
          <a
            href="https://github.com/fal-ai-community/video-starter-kit"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
        </Button>
        {process.env.NEXT_PUBLIC_CUSTOM_KEY && openKeyDialog && (
          <Button
            variant="ghost"
            size="icon"
            className="relative"
            onClick={openKeyDialog}
          >
            {typeof localStorage !== "undefined" &&
              !localStorage?.getItem("falKey") && (
                <span className="dark:bg-orange-400 bg-orange-600 w-2 h-2 rounded-full absolute top-1 right-1"></span>
              )}
            <SettingsIcon className="w-6 h-6" />
          </Button>
        )}
      </nav>
    </header>
  );
}

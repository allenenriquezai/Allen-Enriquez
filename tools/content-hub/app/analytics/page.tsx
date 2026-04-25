"use client";

import { useCallback, useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { MetricsTable, type MetricRow } from "@/components/metrics-table";
import { MetricsChart } from "@/components/metrics-chart";
import { PlatformStatCards } from "@/components/analytics/platform-stat-cards";
import { PostsSection } from "@/components/analytics/posts-section";
import { AddMetricsDialog, type PostOption } from "@/components/analytics/add-metrics-dialog";
import type { YtStat, FbPost, IgPost, TtStat } from "@/components/analytics/platform-tables";

export default function AnalyticsPage() {
  const [rows, setRows] = useState<MetricRow[]>([]);
  const [posts, setPosts] = useState<PostOption[]>([]);
  const [ytStats, setYtStats] = useState<YtStat[]>([]);
  const [ytLoading, setYtLoading] = useState(false);
  const [subscriberCount, setSubscriberCount] = useState<number | null>(null);
  const [fbPosts, setFbPosts] = useState<FbPost[]>([]);
  const [fbLoading, setFbLoading] = useState(false);
  const [igPosts, setIgPosts] = useState<IgPost[]>([]);
  const [igLoading, setIgLoading] = useState(false);
  const [ttStats, setTtStats] = useState<TtStat[]>([]);
  const [ttLoading, setTtLoading] = useState(false);

  const load = useCallback(async () => {
    const res = await fetch("/api/metrics", { cache: "no-store" });
    const json = await res.json();
    setRows(json.metrics ?? []);
  }, []);

  const loadPosts = useCallback(async () => {
    const res = await fetch("/api/posts", { cache: "no-store" });
    const json = await res.json();
    setPosts(json.posts ?? []);
  }, []);

  const loadYouTube = useCallback(async (refresh = false) => {
    setYtLoading(true);
    try {
      const res = await fetch(`/api/analytics/youtube${refresh ? "?refresh=1" : ""}`, { cache: "no-store" });
      const json = await res.json();
      setYtStats(json.stats ?? []);
      if (json.subscriberCount != null) setSubscriberCount(json.subscriberCount);
    } finally {
      setYtLoading(false);
    }
  }, []);

  const loadFacebook = useCallback(async (refresh = false) => {
    setFbLoading(true);
    try {
      const res = await fetch(`/api/analytics/facebook${refresh ? "?refresh=1" : ""}`, { cache: "no-store" });
      const json = await res.json();
      setFbPosts(json.posts ?? []);
    } finally {
      setFbLoading(false);
    }
  }, []);

  const loadInstagram = useCallback(async (refresh = false) => {
    setIgLoading(true);
    try {
      const res = await fetch(`/api/analytics/instagram${refresh ? "?refresh=1" : ""}`, { cache: "no-store" });
      const json = await res.json();
      setIgPosts(json.posts ?? []);
    } finally {
      setIgLoading(false);
    }
  }, []);

  const loadTikTok = useCallback(async (refresh = false) => {
    setTtLoading(true);
    try {
      const res = await fetch(`/api/analytics/tiktok${refresh ? "?refresh=1" : ""}`, { cache: "no-store" });
      const json = await res.json();
      setTtStats(json.stats ?? []);
    } finally {
      setTtLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadPosts(); }, [loadPosts]);
  useEffect(() => { loadYouTube(); }, [loadYouTube]);
  useEffect(() => { loadFacebook(); }, [loadFacebook]);
  useEffect(() => { loadInstagram(); }, [loadInstagram]);
  useEffect(() => { loadTikTok(); }, [loadTikTok]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Platform health overview. Expand Posts to drill into individual content.
          </p>
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList variant="line">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="youtube">YouTube</TabsTrigger>
          <TabsTrigger value="tiktok">TikTok</TabsTrigger>
          <TabsTrigger value="instagram">Instagram</TabsTrigger>
          <TabsTrigger value="facebook">Facebook</TabsTrigger>
          <TabsTrigger value="manual">Manual</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <PlatformStatCards platform="overview" rows={rows} />
          <div className="mt-6">
            <MetricsChart rows={rows} />
          </div>
        </TabsContent>

        <TabsContent value="youtube" className="mt-6">
          <PlatformStatCards
            platform="youtube"
            stats={ytStats}
            subscriberCount={subscriberCount}
          />
          <PostsSection
            platform="youtube"
            stats={ytStats}
            loading={ytLoading}
            onRefresh={() => loadYouTube(true)}
          />
        </TabsContent>

        <TabsContent value="tiktok" className="mt-6">
          <PlatformStatCards platform="tiktok" stats={ttStats} />
          <PostsSection
            platform="tiktok"
            stats={ttStats}
            loading={ttLoading}
            onRefresh={() => loadTikTok(true)}
          />
        </TabsContent>

        <TabsContent value="instagram" className="mt-6">
          <PlatformStatCards platform="instagram" stats={igPosts} />
          <PostsSection
            platform="instagram"
            stats={igPosts}
            loading={igLoading}
            onRefresh={() => loadInstagram(true)}
          />
        </TabsContent>

        <TabsContent value="facebook" className="mt-6">
          <PlatformStatCards platform="facebook" stats={fbPosts} />
          <PostsSection
            platform="facebook"
            stats={fbPosts}
            loading={fbLoading}
            onRefresh={() => loadFacebook(true)}
          />
        </TabsContent>

        <TabsContent value="manual" className="mt-6">
          <div className="flex justify-end mb-4">
            <AddMetricsDialog posts={posts} onSaved={load} />
          </div>
          <MetricsTable rows={rows} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// 由 npm run types:generate 產生，請勿手動編輯。
export interface paths {
    "/api/v1/projects/import/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Preview */
        post: operations["preview_api_v1_projects_import_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/import/commit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Commit */
        post: operations["commit_api_v1_projects_import_commit_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Projects */
        get: operations["list_projects_api_v1_projects_get"];
        put?: never;
        /** Create Project */
        post: operations["create_project_api_v1_projects_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Project */
        get: operations["get_project_api_v1_projects__project_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Project */
        patch: operations["patch_project_api_v1_projects__project_id__patch"];
        trace?: never;
    };
    "/api/v1/projects/{project_id}/archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive Project */
        post: operations["archive_project_api_v1_projects__project_id__archive_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/bulk-shift/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bulk Preview */
        post: operations["bulk_preview_api_v1_projects__project_id__bulk_shift_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/bulk-shift/commit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bulk Commit */
        post: operations["bulk_commit_api_v1_projects__project_id__bulk_shift_commit_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Tasks */
        get: operations["list_tasks_api_v1_tasks_get"];
        put?: never;
        /** Create Task */
        post: operations["create_task_api_v1_tasks_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Task */
        get: operations["get_task_api_v1_tasks__task_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/owner": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Change Owner */
        patch: operations["change_owner_api_v1_tasks__task_id__owner_patch"];
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Set Status */
        post: operations["set_status_api_v1_tasks__task_id__status_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/block": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Set Blocked */
        post: operations["set_blocked_api_v1_tasks__task_id__block_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/adjust-start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Adjust Start */
        post: operations["adjust_start_api_v1_tasks__task_id__adjust_start_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete */
        post: operations["complete_api_v1_tasks__task_id__complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/adjust-due": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Adjust */
        post: operations["adjust_api_v1_tasks__task_id__adjust_due_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/baseline-correction/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Baseline Preview */
        post: operations["baseline_preview_api_v1_tasks__task_id__baseline_correction_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/baseline-correction/commit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Baseline Commit */
        post: operations["baseline_commit_api_v1_tasks__task_id__baseline_correction_commit_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events/{event_id}/annotations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Annotate */
        post: operations["annotate_api_v1_events__event_id__annotations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/stats/time-management": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Time Management */
        get: operations["time_management_api_v1_stats_time_management_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/meta/reasons": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Reasons */
        get: operations["reasons_api_v1_meta_reasons_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/meta/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_v1_meta_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Events */
        get: operations["list_events_api_v1_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Project History */
        get: operations["project_history_api_v1_projects__project_id__history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/gantt": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Project Gantt */
        get: operations["project_gantt_api_v1_projects__project_id__gantt_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ingest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Ingest */
        post: operations["ingest_api_v1_ingest_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ingest/jobs/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Job */
        get: operations["get_job_api_v1_ingest_jobs__job_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/candidates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Candidates */
        get: operations["list_candidates_api_v1_candidates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/candidates/{candidate_id}/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Confirm */
        post: operations["confirm_api_v1_candidates__candidate_id__confirm_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/candidates/{candidate_id}/clarify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Clarify */
        post: operations["clarify_api_v1_candidates__candidate_id__clarify_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/candidates/{candidate_id}/create-task": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Task */
        post: operations["create_task_api_v1_candidates__candidate_id__create_task_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/candidates/{candidate_id}/ignore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Ignore */
        post: operations["ignore_api_v1_candidates__candidate_id__ignore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Settings */
        get: operations["get_settings_api_v1_settings_get"];
        /** Put Settings */
        put: operations["put_settings_api_v1_settings_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings/onboarding/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete Onboarding */
        post: operations["complete_onboarding_api_v1_settings_onboarding_complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/rubrics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Rubrics */
        get: operations["list_rubrics_api_v1_rubrics_get"];
        put?: never;
        /** Confirm Rubric */
        post: operations["confirm_rubric_api_v1_rubrics_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/rubrics/interview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Interview */
        post: operations["interview_api_v1_rubrics_interview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sources/purge": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Purge Sources */
        post: operations["purge_sources_api_v1_sources_purge_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Export
         * @description 直接回傳下載檔，伺服器不落地存檔（SDD 第 6 節）。
         */
        post: operations["export_api_v1_export_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/reports/weekly/draft": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Draft */
        post: operations["draft_api_v1_reports_weekly_draft_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/reports/weekly": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get By Week */
        get: operations["get_by_week_api_v1_reports_weekly_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/reports/weekly/{report_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Report */
        get: operations["get_report_api_v1_reports_weekly__report_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/reports/weekly/{report_id}/manual": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Save Manual */
        put: operations["save_manual_api_v1_reports_weekly__report_id__manual_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/feedback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Feedback */
        get: operations["get_feedback_api_v1_tasks__task_id__feedback_get"];
        /** Save Feedback */
        put: operations["save_feedback_api_v1_tasks__task_id__feedback_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/feedback/pending": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Pending Feedback */
        get: operations["pending_feedback_api_v1_feedback_pending_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/meta/today": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Today */
        get: operations["today_api_v1_meta_today_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AdjustDue */
        AdjustDue: {
            /** Expected Version */
            expected_version: number;
            /**
             * New Due
             * Format: date
             */
            new_due: string;
            /** Reason */
            reason?: string | null;
            /** Note */
            note?: string | null;
            /** Mark */
            mark?: ("better" | "worse" | "none") | null;
            /**
             * Defer Mark
             * @default false
             */
            defer_mark?: boolean;
        };
        /** AdjustDueOut */
        AdjustDueOut: {
            task: components["schemas"]["TaskOut"];
            event: components["schemas"]["EventOut"];
            /** Warnings */
            warnings: string[];
            /** Needs Mark */
            needs_mark: boolean;
        };
        /** AdjustStart */
        AdjustStart: {
            /** Expected Version */
            expected_version: number;
            /**
             * New Start
             * Format: date
             */
            new_start: string;
            /** Note */
            note?: string | null;
        };
        /** AdjustStartOut */
        AdjustStartOut: {
            task: components["schemas"]["TaskOut"];
            event: components["schemas"]["EventOut"];
            /**
             * Warnings
             * @description 可含 START_AFTER_DUE（開始日晚於最新預計日）
             */
            warnings: string[];
        };
        /** Annotation */
        Annotation: {
            /**
             * Mark
             * @enum {string}
             */
            mark: "better" | "worse" | "none";
            /** Reason */
            reason?: string | null;
            /** Note */
            note?: string | null;
        };
        /** AnnotationOut */
        AnnotationOut: {
            event: components["schemas"]["EventOut"];
            /**
             * Effective Mark
             * @enum {string}
             */
            effective_mark: "better" | "worse" | "none";
        };
        /** BaselineCommit */
        BaselineCommit: {
            /** Confirmation Token */
            confirmation_token: string;
            /**
             * Ack
             * @default false
             */
            ack?: boolean;
        };
        /** BaselineImpactOut */
        BaselineImpactOut: {
            orig_due: components["schemas"]["FromToDate"];
            gap_days: components["schemas"]["FromToInt"];
            project_delayed_count: components["schemas"]["FromToInt"];
            /** Past Due Events Kept */
            past_due_events_kept: number;
            /** Old Value Kept In History */
            old_value_kept_in_history: boolean;
        };
        /** BaselinePreview */
        BaselinePreview: {
            /** Expected Version */
            expected_version: number;
            /**
             * New Orig Due
             * Format: date
             */
            new_orig_due: string;
            /**
             * Type
             * @enum {string}
             */
            type: "correction" | "rebaseline";
            /** Reason */
            reason?: string | null;
        };
        /** BaselinePreviewOut */
        BaselinePreviewOut: {
            /** Confirmation Token */
            confirmation_token: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            impact: components["schemas"]["BaselineImpactOut"];
        };
        /** BlockChange */
        BlockChange: {
            /** Expected Version */
            expected_version: number;
            /**
             * Blocked
             * @default true
             */
            blocked?: boolean;
        };
        /** BulkCommitOut */
        BulkCommitOut: {
            /** Batch Id */
            batch_id: number;
            /** Updated */
            updated: number;
            /** Mine Marked */
            mine_marked: number;
            /** Events */
            events: number[];
        };
        /** BulkItem */
        BulkItem: {
            /** Task Id */
            task_id: number;
            /** Expected Version */
            expected_version: number;
        };
        /** BulkPreviewItemOut */
        BulkPreviewItemOut: {
            /** Task Id */
            task_id: number;
            /** Title */
            title: string;
            /** Owner */
            owner: string;
            /**
             * From
             * Format: date
             */
            from: string;
            /**
             * To
             * Format: date
             */
            to: string;
            /** Mine */
            mine: boolean;
            /** Warnings */
            warnings: string[];
        };
        /** BulkPreviewOut */
        BulkPreviewOut: {
            /** Items */
            items: components["schemas"]["BulkPreviewItemOut"][];
            /** Mine Count */
            mine_count: number;
            /** Mark Required */
            mark_required: boolean;
        };
        /** BulkShift */
        BulkShift: {
            /** Items */
            items: components["schemas"]["BulkItem"][];
            /** Days */
            days: number;
            /** Reason */
            reason?: string | null;
            /** Note */
            note?: string | null;
            /** Mark */
            mark?: ("better" | "worse" | "none") | null;
            /**
             * Defer Mark
             * @default false
             */
            defer_mark?: boolean;
        };
        /** CandidateListOut */
        CandidateListOut: {
            /** Items */
            items: components["schemas"]["CandidateOut"][];
            /** Total */
            total: number;
        };
        /** CandidateOut */
        CandidateOut: {
            /** Id */
            id: number;
            /**
             * Kind
             * @enum {string}
             */
            kind: "delay" | "done" | "stuck" | "unclear" | "unmatched";
            /**
             * Certainty
             * @enum {string}
             */
            certainty: "sure" | "to_clarify" | "to_match";
            /**
             * State
             * @enum {string}
             */
            state: "open" | "confirmed" | "ignored";
            task: components["schemas"]["CandidateTaskOut"] | null;
            proposed: components["schemas"]["ProposedOut"] | null;
            /**
             * Quote
             * @description 原文已清除時為 null
             */
            quote: string | null;
            /** Speaker */
            speaker: string;
            /** Spoken At */
            spoken_at: string | null;
            /** Note */
            note: string | null;
            suggest: components["schemas"]["SuggestOut"] | null;
        };
        /** CandidateTaskOut */
        CandidateTaskOut: {
            /** Id */
            id: number;
            /** Title */
            title: string;
            /**
             * Latest Due
             * Format: date
             */
            latest_due: string;
            /**
             * Orig Due
             * Format: date
             */
            orig_due: string;
            /** Version */
            version: number;
        };
        /** CodeLabelOut */
        CodeLabelOut: {
            /** Code */
            code: string;
            /** Label */
            label: string;
        };
        /** ColumnMap */
        ColumnMap: {
            /** Title */
            title: number;
            /** End */
            end: number;
            /** Owner */
            owner?: number | null;
            /** Start */
            start?: number | null;
        };
        /** ColumnMapOut */
        ColumnMapOut: {
            /** Title */
            title: number | null;
            /** Owner */
            owner: number | null;
            /** Start */
            start: number | null;
            /** End */
            end: number | null;
            /**
             * Mapped By
             * @description 必填欄位對應不到時為 null，rows 為空
             */
            mapped_by: ("rule" | "ai" | "manual") | null;
            /**
             * Ai Run Id
             * @description mapped_by 為 ai 時才出現；commit 時與 column_map 一起送回（12.7 D-3）
             */
            ai_run_id?: number | null;
        };
        /** CommitIn */
        CommitIn: {
            /**
             * Target
             * @default new
             */
            target?: "new" | number;
            /** New Name */
            new_name?: string | null;
            /** Rows */
            rows: components["schemas"]["CommitRow"][];
            /** Ai Run Id */
            ai_run_id?: number | null;
            column_map?: components["schemas"]["ColumnMap"] | null;
        };
        /** CommitRow */
        CommitRow: {
            /** Index */
            index: number;
            /** Title */
            title?: string | null;
            /** Owner */
            owner?: string | null;
            /** Start */
            start?: string | null;
            /** End */
            end?: string | null;
            /**
             * Skip
             * @default false
             */
            skip?: boolean;
        };
        /** Complete */
        Complete: {
            /** Expected Version */
            expected_version: number;
            /** Done Date */
            done_date?: string | null;
        };
        /** CompleteOut */
        CompleteOut: {
            task: components["schemas"]["TaskOut"];
            event: components["schemas"]["EventOut"];
            /** Feedback Required */
            feedback_required: boolean;
        };
        /** ConfirmIn */
        ConfirmIn: {
            /** Expected Version */
            expected_version: number;
            /** New Due */
            new_due?: string | null;
        };
        /** CountDays */
        CountDays: {
            /** Count */
            count: number;
            /** Days */
            days: number;
        };
        /** CreateTaskIn */
        CreateTaskIn: {
            /** Title */
            title: string;
            /**
             * Due
             * Format: date
             */
            due: string;
            /** Owner */
            owner?: string | null;
            /** Project Id */
            project_id?: number | null;
        };
        /** DecideOut */
        DecideOut: {
            candidate: components["schemas"]["CandidateOut"];
            /** @description 忽略時不出現 */
            task?: components["schemas"]["TaskOut"] | null;
            /** @description 忽略、建任務時不出現 */
            event?: components["schemas"]["EventOut"] | null;
            /**
             * Needs Mark
             * @description 確認延期時才出現
             */
            needs_mark?: boolean | null;
            /**
             * Warnings
             * @description 確認延期、建任務時出現；確認延期可含 BEFORE_START（新日期早於開始日）；建任務可含 PROJECT_ARCHIVED（沿用的候選專案已封存，任務已建為無專案）
             */
            warnings?: string[] | null;
            /**
             * Feedback Required
             * @description 確認完成時才出現
             */
            feedback_required?: boolean | null;
        };
        /** DueReasonOut */
        DueReasonOut: {
            /** Code */
            code: string;
            /** Label */
            label: string;
            /**
             * Direction
             * @enum {string}
             */
            direction: "earlier" | "later";
            /** External */
            external: boolean;
        };
        /** EnergyDistribution */
        EnergyDistribution: {
            /** High */
            high: number;
            /** Mid */
            mid: number;
            /** Low */
            low: number;
            /** Not Done */
            not_done: number;
        };
        /** EventOut */
        EventOut: {
            /** Id */
            id: number;
            /**
             * Ts
             * Format: date-time
             */
            ts: string;
            /** Project Id */
            project_id: number | null;
            /** Task Id */
            task_id: number | null;
            /** Task Title */
            task_title: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "due" | "annotation" | "status" | "task" | "feedback" | "goal" | "baseline" | "project";
            /** Field */
            field: string;
            /** From Value */
            from_value: string | null;
            /** To Value */
            to_value: string | null;
            /**
             * Origin
             * @enum {string}
             */
            origin: "candidate" | "manual" | "bulk" | "import" | "baseline_correction" | "system";
            /** Origin Ref */
            origin_ref: number | null;
            /** Source Id */
            source_id: number | null;
            /** Reason */
            reason: string | null;
            /** Note */
            note: string | null;
            /** Delta Days */
            delta_days: number | null;
            /** Mark */
            mark: ("better" | "worse" | "none") | null;
            /** Mine */
            mine: boolean;
            /** Ref Event Id */
            ref_event_id: number | null;
            /** Batch Id */
            batch_id: number | null;
            /** Actor */
            actor: string;
            /** Extra */
            extra: {
                [key: string]: unknown;
            } | null;
        };
        /** ExportOut */
        ExportOut: {
            /**
             * Exported At
             * Format: date-time
             */
            exported_at: string;
            /** Schema Version */
            schema_version: string | null;
            /** Counts */
            counts: {
                [key: string]: number;
            };
            /** Tables */
            tables: {
                [key: string]: {
                    [key: string]: unknown;
                }[];
            };
        };
        /** FeedbackOut */
        FeedbackOut: {
            /** Id */
            id: number;
            /** Task Id */
            task_id: number;
            /** Actual Stars */
            actual_stars: number;
            /**
             * Energy
             * @enum {string}
             */
            energy: "high" | "mid" | "low";
            /** Invest Vs Expected */
            invest_vs_expected: ("less" | "as_expected" | "more") | null;
            /**
             * Overdue Days
             * @description 伺服器計算：max(0, done_date − orig_due)
             */
            overdue_days: number;
            /** Rubric Id */
            rubric_id: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * FeedbackSave
         * @description 不收 goal_id（關聯走 POST /goal-links，#47 A6）；overdue_days 等伺服器欄位送了也忽略。
         */
        FeedbackSave: {
            /** Actual Stars */
            actual_stars: number;
            /**
             * Energy
             * @enum {string}
             */
            energy: "high" | "mid" | "low";
            /** Invest Vs Expected */
            invest_vs_expected?: ("less" | "as_expected" | "more") | null;
            /** Rubric Id */
            rubric_id: number;
        };
        /** FeedbackSaveOut */
        FeedbackSaveOut: {
            feedback: components["schemas"]["FeedbackOut"];
            event: components["schemas"]["EventOut"];
        };
        /** FromToDate */
        FromToDate: {
            /**
             * From
             * Format: date
             */
            from: string;
            /**
             * To
             * Format: date
             */
            to: string;
        };
        /** FromToInt */
        FromToInt: {
            /** From */
            from: number;
            /** To */
            to: number;
        };
        /** GanttOut */
        GanttOut: {
            /** @description 沒有任務時為 null */
            range: components["schemas"]["FromToDate"] | null;
            /**
             * Today
             * Format: date
             */
            today: string;
            summary: components["schemas"]["GanttSummary"];
            /** Rows */
            rows: components["schemas"]["GanttRowOut"][];
        };
        /** GanttRowOut */
        GanttRowOut: {
            /** Task Id */
            task_id: number;
            /** Title */
            title: string;
            /** Owner */
            owner: string;
            /**
             * Status
             * @enum {string}
             */
            status: "todo" | "doing" | "done";
            /**
             * Start
             * Format: date
             */
            start: string;
            /**
             * Orig Due
             * Format: date
             */
            orig_due: string;
            /**
             * Latest Due
             * Format: date
             */
            latest_due: string;
            /** Delta Days */
            delta_days: number;
            /** Done Date */
            done_date: string | null;
            /** Blocked */
            blocked: boolean;
            /** Version */
            version: number;
        };
        /** GanttSummary */
        GanttSummary: {
            /** Done */
            done: number;
            /** Total */
            total: number;
            /** Delayed */
            delayed: number;
            /** Open Candidates */
            open_candidates: number;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HealthOut */
        HealthOut: {
            /**
             * Db
             * @enum {string}
             */
            db: "ok" | "error";
            /**
             * Ai
             * @enum {string}
             */
            ai: "ok" | "unavailable";
        };
        /** HistoryItemOut */
        HistoryItemOut: {
            /** Id */
            id: number;
            /**
             * Ts
             * Format: date-time
             */
            ts: string;
            /** Project Id */
            project_id: number | null;
            /** Task Id */
            task_id: number | null;
            /** Task Title */
            task_title: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "due" | "annotation" | "status" | "task" | "feedback" | "goal" | "baseline" | "project";
            /** Field */
            field: string;
            /** From Value */
            from_value: string | null;
            /** To Value */
            to_value: string | null;
            /**
             * Origin
             * @enum {string}
             */
            origin: "candidate" | "manual" | "bulk" | "import" | "baseline_correction" | "system";
            /** Origin Ref */
            origin_ref: number | null;
            /** Source Id */
            source_id: number | null;
            /** Reason */
            reason: string | null;
            /** Note */
            note: string | null;
            /** Delta Days */
            delta_days: number | null;
            /** Mark */
            mark: ("better" | "worse" | "none") | null;
            /** Mine */
            mine: boolean;
            /** Ref Event Id */
            ref_event_id: number | null;
            /** Batch Id */
            batch_id: number | null;
            /** Actor */
            actor: string;
            /** Extra */
            extra: {
                [key: string]: unknown;
            } | null;
            /** Project Name */
            project_name: string | null;
            /** Effective Mark */
            effective_mark: ("better" | "worse" | "none") | null;
            source: components["schemas"]["SourceRefOut"];
        };
        /** HistoryListOut */
        HistoryListOut: {
            /** Items */
            items: components["schemas"]["HistoryItemOut"][];
            /** Total */
            total: number;
        };
        /** ImportCommitOut */
        ImportCommitOut: {
            /** Project Id */
            project_id: number;
            /** Created */
            created: number;
            /** Skipped */
            skipped: number;
            /** Event Id */
            event_id: number;
        };
        /** ImportIssueOut */
        ImportIssueOut: {
            /**
             * Level
             * @enum {string}
             */
            level: "error" | "warn";
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /** ImportPreviewOut */
        ImportPreviewOut: {
            /**
             * Ai Status
             * @enum {string}
             */
            ai_status: "ok" | "unavailable" | "invalid_output";
            /** Header */
            header: string[];
            column_map: components["schemas"]["ColumnMapOut"];
            /** Rows */
            rows: components["schemas"]["ImportRowOut"][];
            summary: components["schemas"]["ImportSummary"];
        };
        /** ImportRowOut */
        ImportRowOut: {
            /** Index */
            index: number;
            /** Title */
            title: string;
            /** Owner */
            owner: string;
            /** Start */
            start: string | null;
            /** End */
            end: string | null;
            /** Blocking */
            blocking: boolean;
            /** Issues */
            issues: components["schemas"]["ImportIssueOut"][];
        };
        /** ImportSummary */
        ImportSummary: {
            /** Importable */
            importable: number;
            /** Blocking */
            blocking: number;
        };
        /** IngestAsyncOut */
        IngestAsyncOut: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            mode: "async";
            /** Job Id */
            job_id: number;
            /**
             * Status
             * @constant
             */
            status: "queued";
        };
        /** IngestIn */
        IngestIn: {
            /** Text */
            text: string;
            /** Project Id */
            project_id?: number | null;
        };
        /** IngestJobOut */
        IngestJobOut: {
            /** Id */
            id: number;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "succeeded" | "failed";
            /** Attempts */
            attempts: number;
            result: components["schemas"]["IngestJobResult"] | null;
            /** Error */
            error: string | null;
        };
        /** IngestJobResult */
        IngestJobResult: {
            /** Created */
            created: number;
            /** Skipped */
            skipped: number;
            /** Duplicates */
            duplicates: number;
            /** Unparsed Lines */
            unparsed_lines: number[];
            /**
             * Ai Status
             * @enum {string}
             */
            ai_status: "ok" | "unavailable" | "invalid_output";
            /** Candidate Ids */
            candidate_ids: number[];
        };
        /** IngestSummary */
        IngestSummary: {
            /** Created */
            created: number;
            /** Skipped */
            skipped: number;
            /** Duplicates */
            duplicates: number;
            /** Unparsed Lines */
            unparsed_lines: number[];
        };
        /** IngestSyncOut */
        IngestSyncOut: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            mode: "sync";
            /**
             * Ai Status
             * @enum {string}
             */
            ai_status: "ok" | "unavailable" | "invalid_output";
            result: components["schemas"]["IngestSummary"];
            /** Candidates */
            candidates: components["schemas"]["CandidateOut"][];
        };
        /** InterviewAnswers */
        InterviewAnswers: {
            /** Q1 */
            q1: string;
            /** Q2 */
            q2: string;
            /** Q3 */
            q3: string;
        };
        /** InterviewIn */
        InterviewIn: {
            /** Q1 */
            q1: string;
            /** Q2 */
            q2: string;
            /** Q3 */
            q3: string;
        };
        /** InterviewRecord */
        InterviewRecord: {
            /** Q1 */
            q1: string;
            /** Q2 */
            q2: string;
            /** Q3 */
            q3: string;
            /** Draft */
            draft?: string[] | null;
        };
        /** ManualText */
        ManualText: {
            /** Manual Text */
            manual_text: string | null;
        };
        /** OnboardingIn */
        OnboardingIn: {
            /**
             * Skipped
             * @default false
             */
            skipped?: boolean;
        };
        /** OwnerChange */
        OwnerChange: {
            /** Expected Version */
            expected_version: number;
            /** Owner */
            owner: string;
        };
        /** PendingFeedbackItem */
        PendingFeedbackItem: {
            /** Task Id */
            task_id: number;
            /** Title */
            title: string;
            /** Owner */
            owner: string;
            /** Project Id */
            project_id: number | null;
            /**
             * Done Date
             * Format: date
             */
            done_date: string;
            /**
             * Orig Due
             * Format: date
             */
            orig_due: string;
            /** Overdue Days */
            overdue_days: number;
            /** Expected Stars */
            expected_stars: number;
            /**
             * Star Source
             * @enum {string}
             */
            star_source: "self" | "ai_accepted" | "ai_edited" | "import_default";
        };
        /** PendingFeedbackOut */
        PendingFeedbackOut: {
            /** Items */
            items: components["schemas"]["PendingFeedbackItem"][];
            /** Total */
            total: number;
        };
        /** PreviewIn */
        PreviewIn: {
            /** Text */
            text: string;
            /**
             * Target
             * @default new
             */
            target?: "new" | number;
            /** New Name */
            new_name?: string | null;
            column_map?: components["schemas"]["ColumnMap"] | null;
        };
        /** ProjectCreate */
        ProjectCreate: {
            /** Name */
            name: string;
            /**
             * Scope
             * @default work
             * @enum {string}
             */
            scope?: "work" | "private";
            /**
             * Audience
             * @default manager
             * @enum {string}
             */
            audience?: "manager" | "client" | "none";
            /** Line Group Id */
            line_group_id?: number | null;
        };
        /** ProjectDetailOut */
        ProjectDetailOut: {
            /** Id */
            id: number;
            /** Name */
            name: string;
            /**
             * Scope
             * @enum {string}
             */
            scope: "work" | "private";
            /**
             * Audience
             * @enum {string}
             */
            audience: "manager" | "client" | "none";
            /** Line Group Id */
            line_group_id: number | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Archived At */
            archived_at: string | null;
            /** Task Count */
            task_count: number;
            /** Baseline Saved At */
            baseline_saved_at: string | null;
        };
        /** ProjectListOut */
        ProjectListOut: {
            /** Items */
            items: components["schemas"]["ProjectOut"][];
            /** Total */
            total: number;
        };
        /** ProjectOut */
        ProjectOut: {
            /** Id */
            id: number;
            /** Name */
            name: string;
            /**
             * Scope
             * @enum {string}
             */
            scope: "work" | "private";
            /**
             * Audience
             * @enum {string}
             */
            audience: "manager" | "client" | "none";
            /** Line Group Id */
            line_group_id: number | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Archived At */
            archived_at: string | null;
        };
        /** ProjectPatch */
        ProjectPatch: {
            /** Name */
            name?: string | null;
            /** Scope */
            scope?: ("work" | "private") | null;
            /** Audience */
            audience?: ("manager" | "client" | "none") | null;
        };
        /** ProjectPatchOut */
        ProjectPatchOut: {
            project: components["schemas"]["ProjectOut"];
            /** Changes */
            changes: components["schemas"]["EventOut"][];
        };
        /** ProposedOut */
        ProposedOut: {
            /** New Due */
            new_due?: string | null;
        };
        /** PurgeIn */
        PurgeIn: {
            /** Confirm */
            confirm: boolean;
        };
        /** PurgeOut */
        PurgeOut: {
            /** Purged */
            purged: number;
        };
        /** ReasonsOut */
        ReasonsOut: {
            /** Due */
            due: components["schemas"]["DueReasonOut"][];
            /** Baseline Types */
            baseline_types: components["schemas"]["CodeLabelOut"][];
            /** Baseline Reasons */
            baseline_reasons: components["schemas"]["CodeLabelOut"][];
        };
        /** RubricCreatedOut */
        RubricCreatedOut: {
            /** Id */
            id: number;
            /** Version */
            version: number;
        };
        /** RubricDraftOut */
        RubricDraftOut: {
            /**
             * Ai Status
             * @constant
             */
            ai_status: "ok";
            /** Draft */
            draft: string[];
        };
        /** RubricIn */
        RubricIn: {
            /** Levels */
            levels: string[];
            interview: components["schemas"]["InterviewRecord"];
        };
        /** RubricListOut */
        RubricListOut: {
            /** Items */
            items: components["schemas"]["RubricOut"][];
            /** Total */
            total: number;
        };
        /** RubricOut */
        RubricOut: {
            /** Id */
            id: number;
            /** Version */
            version: number;
            /** Levels */
            levels: string[];
            /**
             * Source
             * @enum {string}
             */
            source: "default" | "interview";
            interview: components["schemas"]["InterviewAnswers"] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** SettingsOut */
        SettingsOut: {
            /**
             * Default Scope
             * @enum {string}
             */
            default_scope: "work" | "private";
            /**
             * Role
             * @enum {string}
             */
            role: "project_owner" | "wbs_owner" | "both";
            /**
             * Report Audience
             * @enum {string}
             */
            report_audience: "manager" | "client" | "none";
            /** Confirm Time */
            confirm_time: string;
            /** Confirm Cap Min */
            confirm_cap_min: number;
            /**
             * Remind Default
             * @enum {string}
             */
            remind_default: "morning" | "eve_before" | "none";
            /** Retention Days */
            retention_days: number;
            /** Energy Def High */
            energy_def_high: string;
            /** Energy Def Mid */
            energy_def_mid: string;
            /** Energy Def Low */
            energy_def_low: string;
            /** Goal Types Enabled */
            goal_types_enabled: ("growth" | "time" | "expectation")[];
            /** Onboarded At */
            onboarded_at: string | null;
        };
        /** SettingsPatch */
        SettingsPatch: {
            /** Default Scope */
            default_scope?: ("work" | "private") | null;
            /** Role */
            role?: ("project_owner" | "wbs_owner" | "both") | null;
            /** Report Audience */
            report_audience?: ("manager" | "client" | "none") | null;
            /** Confirm Time */
            confirm_time?: ("12:00" | "18:00" | "21:00") | null;
            /** Confirm Cap Min */
            confirm_cap_min?: (3 | 5 | 10) | null;
            /** Remind Default */
            remind_default?: ("morning" | "eve_before" | "none") | null;
            /** Retention Days */
            retention_days?: (30 | 90 | 180) | null;
            /** Energy Def High */
            energy_def_high?: string | null;
            /** Energy Def Mid */
            energy_def_mid?: string | null;
            /** Energy Def Low */
            energy_def_low?: string | null;
            /** Goal Types Enabled */
            goal_types_enabled?: ("growth" | "time" | "expectation")[] | null;
        };
        /** SourceRefOut */
        SourceRefOut: {
            /** Label */
            label: string;
            /**
             * Quote
             * @description 原文已清除或沒有來源時為 null
             */
            quote: string | null;
            /** Purged */
            purged: boolean;
        };
        /** StatusChange */
        StatusChange: {
            /** Expected Version */
            expected_version: number;
            /**
             * Status
             * @enum {string}
             */
            status: "todo" | "doing";
        };
        /** SuggestOut */
        SuggestOut: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "delay" | "done" | "stuck";
            /** New Due */
            new_due?: string | null;
        };
        /** TaskCreate */
        TaskCreate: {
            /** Title */
            title: string;
            /**
             * Due
             * Format: date
             */
            due: string;
            /**
             * Owner
             * @default 我
             */
            owner?: string;
            /** Scope */
            scope?: ("work" | "private") | null;
            /** Project Id */
            project_id?: number | null;
            /** Start */
            start?: string | null;
            /**
             * Done When
             * @default
             */
            done_when?: string;
            /**
             * Remind
             * @default morning
             * @enum {string}
             */
            remind?: "morning" | "eve_before" | "none";
            /** Goal Id */
            goal_id?: number | null;
            /**
             * Expected Stars
             * @default 3
             */
            expected_stars?: number;
            /** Suggested Stars */
            suggested_stars?: number | null;
        };
        /** TaskDetailOut */
        TaskDetailOut: {
            task: components["schemas"]["TaskOut"];
            /** Events */
            events: components["schemas"]["EventOut"][];
        };
        /** TaskEventOut */
        TaskEventOut: {
            task: components["schemas"]["TaskOut"];
            event: components["schemas"]["EventOut"];
        };
        /** TaskListOut */
        TaskListOut: {
            /** Items */
            items: components["schemas"]["TaskOut"][];
            /** Total */
            total: number;
        };
        /** TaskOut */
        TaskOut: {
            /** Id */
            id: number;
            /** Project Id */
            project_id: number | null;
            /** Title */
            title: string;
            /** Owner */
            owner: string;
            /**
             * Scope
             * @enum {string}
             */
            scope: "work" | "private";
            /**
             * Start
             * Format: date
             */
            start: string;
            /**
             * Orig Due
             * Format: date
             */
            orig_due: string;
            /**
             * Latest Due
             * Format: date
             */
            latest_due: string;
            /**
             * Delta Days
             * @description latest_due − orig_due（天）
             */
            delta_days: number;
            /**
             * Status
             * @enum {string}
             */
            status: "todo" | "doing" | "done";
            /** Blocked */
            blocked: boolean;
            /** Done Date */
            done_date: string | null;
            /** Done When */
            done_when: string;
            /**
             * Remind
             * @enum {string}
             */
            remind: "morning" | "eve_before" | "none";
            /** Expected Stars */
            expected_stars: number;
            /**
             * Star Source
             * @enum {string}
             */
            star_source: "self" | "ai_accepted" | "ai_edited" | "import_default";
            /** Rubric Id */
            rubric_id: number | null;
            /** Goal Id */
            goal_id: number | null;
            /** Version */
            version: number;
        };
        /** TimeMgmtStatsOut */
        TimeMgmtStatsOut: {
            better: components["schemas"]["CountDays"];
            worse: components["schemas"]["CountDays"];
            /** None */
            none: number;
            /** Unmarked */
            unmarked: number;
            worse_by_energy: components["schemas"]["EnergyDistribution"];
            /** Min Sample */
            min_sample: number;
            /**
             * Judgement
             * @description 樣本不足 min_sample 時為 null；規則見 spec FR-MRK-07
             */
            judgement: string | null;
            /**
             * Judgement Note
             * @description 判讀說明：樣本不足的說明，或變好／變差次數＋精力洞察（FR-MRK-07）
             */
            judgement_note: string;
        };
        /** TodayOut */
        TodayOut: {
            /**
             * Today
             * Format: date
             * @description 伺服器的今天（台北時區）
             */
            today: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** WeeklyDraft */
        WeeklyDraft: {
            /**
             * Week Start
             * Format: date
             */
            week_start: string;
        };
        /**
         * WeeklyEventOut
         * @description 事件證據：只有時間與前值、後值、天數；不含原因、備註、註記與原句（spec 5.14）。
         */
        WeeklyEventOut: {
            /** Id */
            id: number;
            /**
             * Ts
             * Format: date-time
             */
            ts: string;
            /** From Value */
            from_value: string | null;
            /** To Value */
            to_value: string | null;
            /** Delta Days */
            delta_days: number | null;
        };
        /**
         * WeeklyItemOut
         * @description 不屬於該段的欄位為 null（spec 5.14 表）；可讀內容是讀取時的任務現值。
         */
        WeeklyItemOut: {
            /**
             * Section
             * @enum {string}
             */
            section: "done" | "delay" | "next";
            /** Task Id */
            task_id: number;
            /**
             * Event Id
             * @description next 項目為 null
             */
            event_id: number | null;
            /** Title */
            title: string | null;
            /** Owner */
            owner: string | null;
            /**
             * Done Date
             * @description 只有 done
             */
            done_date: string | null;
            /**
             * Orig Due
             * @description 只有 delay
             */
            orig_due: string | null;
            /**
             * Latest Due
             * @description delay、next
             */
            latest_due: string | null;
            /**
             * Blocked
             * @description 只有 next
             */
            blocked: boolean | null;
            /** @description done 為完成事件、delay 為延後事件；next 為 null */
            event: components["schemas"]["WeeklyEventOut"] | null;
        };
        /** WeeklyReportOut */
        WeeklyReportOut: {
            /** Id */
            id: number;
            /**
             * Week Start
             * Format: date
             */
            week_start: string;
            /** Ai Status */
            ai_status: ("ok" | "unavailable" | "invalid_output") | null;
            /**
             * Excluded Private
             * @description 產生初稿當下送 AI 前排除的私人任務數（AC-48）
             */
            excluded_private: number;
            /**
             * Draft
             * @description validated=false 時為 null
             */
            draft: string | null;
            /**
             * Items
             * @description validated=true 為 AI 項目，否則為依歷程列出的事件清單
             */
            items: components["schemas"]["WeeklyItemOut"][];
            /** Validated */
            validated: boolean;
            /** Manual Text */
            manual_text: string | null;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    preview_api_v1_projects_import_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PreviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportPreviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    commit_api_v1_projects_import_commit_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CommitIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportCommitOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_projects_api_v1_projects_get: {
        parameters: {
            query?: {
                include_archived?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_project_api_v1_projects_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_project_api_v1_projects__project_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_project_api_v1_projects__project_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectPatchOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_project_api_v1_projects__project_id__archive_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    bulk_preview_api_v1_projects__project_id__bulk_shift_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BulkShift"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BulkPreviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    bulk_commit_api_v1_projects__project_id__bulk_shift_commit_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BulkShift"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BulkCommitOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_tasks_api_v1_tasks_get: {
        parameters: {
            query?: {
                project_id?: string | null;
                owner?: string | null;
                status?: string | null;
                scope?: string | null;
                due_before?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_task_api_v1_tasks_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TaskCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_task_api_v1_tasks__task_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    change_owner_api_v1_tasks__task_id__owner_patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OwnerChange"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskEventOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_status_api_v1_tasks__task_id__status_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StatusChange"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskEventOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_blocked_api_v1_tasks__task_id__block_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BlockChange"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskEventOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    adjust_start_api_v1_tasks__task_id__adjust_start_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AdjustStart"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdjustStartOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    complete_api_v1_tasks__task_id__complete_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Complete"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompleteOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    adjust_api_v1_tasks__task_id__adjust_due_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AdjustDue"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdjustDueOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    baseline_preview_api_v1_tasks__task_id__baseline_correction_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BaselinePreview"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BaselinePreviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    baseline_commit_api_v1_tasks__task_id__baseline_correction_commit_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BaselineCommit"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskEventOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    annotate_api_v1_events__event_id__annotations_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Annotation"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnnotationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    time_management_api_v1_stats_time_management_get: {
        parameters: {
            query?: {
                from?: string | null;
                to?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TimeMgmtStatsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reasons_api_v1_meta_reasons_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReasonsOut"];
                };
            };
        };
    };
    health_api_v1_meta_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthOut"];
                };
            };
        };
    };
    list_events_api_v1_events_get: {
        parameters: {
            query?: {
                project_id?: string | null;
                kind?: ("due" | "annotation" | "status" | "task" | "feedback" | "goal" | "baseline" | "project") | null;
                task_id?: number | null;
                batch_id?: number | null;
                from?: string | null;
                to?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HistoryListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    project_history_api_v1_projects__project_id__history_get: {
        parameters: {
            query?: {
                kind?: ("due" | "annotation" | "status" | "task" | "feedback" | "goal" | "baseline" | "project") | null;
                task_id?: number | null;
                batch_id?: number | null;
                from?: string | null;
                to?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: never;
            path: {
                project_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HistoryListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    project_gantt_api_v1_projects__project_id__gantt_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GanttOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ingest_api_v1_ingest_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IngestIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IngestSyncOut"] | components["schemas"]["IngestAsyncOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_job_api_v1_ingest_jobs__job_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IngestJobOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_candidates_api_v1_candidates_get: {
        parameters: {
            query?: {
                state?: "open" | "confirmed" | "ignored";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CandidateListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    confirm_api_v1_candidates__candidate_id__confirm_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                candidate_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConfirmIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecideOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    clarify_api_v1_candidates__candidate_id__clarify_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                candidate_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConfirmIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecideOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_task_api_v1_candidates__candidate_id__create_task_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                candidate_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateTaskIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecideOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ignore_api_v1_candidates__candidate_id__ignore_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                candidate_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecideOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_settings_api_v1_settings_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SettingsOut"];
                };
            };
        };
    };
    put_settings_api_v1_settings_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SettingsPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SettingsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    complete_onboarding_api_v1_settings_onboarding_complete_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OnboardingIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SettingsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_rubrics_api_v1_rubrics_get: {
        parameters: {
            query?: {
                active?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RubricListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    confirm_rubric_api_v1_rubrics_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RubricIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RubricCreatedOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    interview_api_v1_rubrics_interview_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InterviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RubricDraftOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    purge_sources_api_v1_sources_purge_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PurgeIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PurgeOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_api_v1_export_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 下載檔（Content-Disposition: attachment） */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExportOut"];
                };
            };
        };
    };
    draft_api_v1_reports_weekly_draft_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WeeklyDraft"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WeeklyReportOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_by_week_api_v1_reports_weekly_get: {
        parameters: {
            query: {
                week_start: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WeeklyReportOut"];
                };
            };
            /** @description 該週尚未產生（正常狀態，不是錯誤；spec 5.14） */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_report_api_v1_reports_weekly__report_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                report_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WeeklyReportOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    save_manual_api_v1_reports_weekly__report_id__manual_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                report_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ManualText"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WeeklyReportOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_feedback_api_v1_tasks__task_id__feedback_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedbackOut"];
                };
            };
            /** @description 任務存在時代表尚未填寫（正常狀態）；或任務不存在（NOT_FOUND） */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    save_feedback_api_v1_tasks__task_id__feedback_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FeedbackSave"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedbackSaveOut"];
                };
            };
            /** @description 任務不存在（NOT_FOUND） */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 任務已有完成回報（FEEDBACK_EXISTS；修改回報 9.3 未開放） */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pending_feedback_api_v1_feedback_pending_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PendingFeedbackOut"];
                };
            };
        };
    };
    today_api_v1_meta_today_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TodayOut"];
                };
            };
        };
    };
}

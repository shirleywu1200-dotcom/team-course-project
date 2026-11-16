// 由 npm run types:generate 產生，請勿手動編輯。
export interface paths {
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
        /** CodeLabelOut */
        CodeLabelOut: {
            /** Code */
            code: string;
            /** Label */
            label: string;
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
        /** CountDays */
        CountDays: {
            /** Count */
            count: number;
            /** Days */
            days: number;
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
        /** OwnerChange */
        OwnerChange: {
            /** Expected Version */
            expected_version: number;
            /** Owner */
            owner: string;
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
        /** ReasonsOut */
        ReasonsOut: {
            /** Due */
            due: components["schemas"]["DueReasonOut"][];
            /** Baseline Types */
            baseline_types: components["schemas"]["CodeLabelOut"][];
            /** Baseline Reasons */
            baseline_reasons: components["schemas"]["CodeLabelOut"][];
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
            /** Judgement */
            judgement: string | null;
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
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
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
}

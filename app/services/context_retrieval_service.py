import json
import logging
import re
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.models.context_models import ContextRetrievalRequest, MatchedContextItem, RetrievedContextPacket


logger = logging.getLogger(__name__)


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class ContextRetrievalService:
    def is_configured(self) -> bool:
        return bool(get_settings().policysphere_lab_path)

    def run(self, request: ContextRetrievalRequest) -> RetrievedContextPacket:
        settings = get_settings()
        configured_path = settings.policysphere_lab_path

        if not configured_path:
            logger.info("context retrieval skipped because POLICYSPHERE_LAB_PATH is not configured")
            return self._empty_packet("POLICYSPHERE_LAB_PATH is not configured.")

        root_path = Path(configured_path).expanduser()
        if not root_path.exists() or not root_path.is_dir():
            logger.warning("context retrieval skipped because configured path is invalid path=%s", configured_path)
            return self._empty_packet(f"Configured PolicySphere path is invalid: {configured_path}")

        manifest_path = root_path / "knowledge" / "system-manifest.json"
        if not manifest_path.exists():
            logger.warning("context retrieval skipped because manifest file is missing path=%s", str(manifest_path))
            return self._empty_packet(f"Manifest file not found: {manifest_path.as_posix()}")

        try:
            manifest = self._load_json_file(manifest_path)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("context retrieval skipped because manifest could not be loaded path=%s", str(manifest_path))
            return self._empty_packet(f"Manifest file could not be loaded: {manifest_path.as_posix()}. {exc}")

        source_files_loaded: list[str] = [manifest_path.as_posix()]
        supporting_collections = self._load_supporting_collections(root_path, manifest, source_files_loaded)
        normalized_request = self._normalize_request_text(request)
        request_tokens = self._tokenize(normalized_request)

        feature_records = self._build_feature_records(manifest, supporting_collections)
        feature_matches = self._match_items(
            request_tokens=request_tokens,
            items=feature_records,
            artifact_type="feature",
        )

        linked_ids = self._collect_linked_ids(feature_matches, feature_records)
        ui_matches = self._match_items(
            request_tokens=request_tokens,
            items=self._build_records_from_collection(
                supporting_collections.get("ui_screens"),
                default_name_fields=("name", "screen_name"),
                artifact_type="ui_screen",
            ),
            artifact_type="ui_screen",
            linked_ids=linked_ids.get("ui_screen", set()),
        )
        api_matches = self._match_items(
            request_tokens=request_tokens,
            items=self._build_records_from_collection(
                supporting_collections.get("api_endpoints"),
                default_name_fields=("name", "path", "endpoint"),
                artifact_type="api_endpoint",
            ),
            artifact_type="api_endpoint",
            linked_ids=linked_ids.get("api_endpoint", set()),
        )
        db_matches = self._match_items(
            request_tokens=request_tokens,
            items=self._build_records_from_collection(
                supporting_collections.get("database_tables"),
                default_name_fields=("name", "table_name"),
                artifact_type="database_table",
            ),
            artifact_type="database_table",
            linked_ids=linked_ids.get("database_table", set()),
        )
        business_rule_matches = self._match_items(
            request_tokens=request_tokens,
            items=self._build_records_from_collection(
                supporting_collections.get("business_rules"),
                default_name_fields=("name", "rule_name", "title"),
                artifact_type="business_rule",
            ),
            artifact_type="business_rule",
            linked_ids=linked_ids.get("business_rule", set()),
        )
        automation_matches = self._match_items(
            request_tokens=request_tokens,
            items=self._build_records_from_collection(
                supporting_collections.get("automation_tests"),
                default_name_fields=("name", "test_name", "class_name"),
                artifact_type="automation_test",
            ),
            artifact_type="automation_test",
            linked_ids=linked_ids.get("automation_test", set()),
        )
        defect_matches = self._match_items(
            request_tokens=request_tokens,
            items=self._build_records_from_collection(
                supporting_collections.get("known_defects"),
                default_name_fields=("name", "title", "defect_title"),
                artifact_type="known_defect",
            ),
            artifact_type="known_defect",
            linked_ids=linked_ids.get("known_defect", set()),
        )
        test_history_matches = self._match_items(
            request_tokens=request_tokens,
            items=self._build_records_from_collection(
                supporting_collections.get("test_history"),
                default_name_fields=("name", "title", "history_name"),
                artifact_type="test_history",
            ),
            artifact_type="test_history",
            linked_ids=linked_ids.get("test_history", set()),
        )

        risk_areas = self._collect_risk_areas(feature_matches, feature_records)
        open_questions = self._build_open_questions(
            feature_matches,
            ui_matches,
            api_matches,
            db_matches,
            business_rule_matches,
            automation_matches,
            defect_matches,
            test_history_matches,
        )
        retrieval_confidence = self._derive_confidence(
            feature_matches,
            ui_matches,
            api_matches,
            db_matches,
            business_rule_matches,
            automation_matches,
            defect_matches,
            test_history_matches,
        )

        packet = RetrievedContextPacket(
            matched_features=feature_matches,
            matched_ui_screens=ui_matches,
            matched_api_endpoints=api_matches,
            matched_database_tables=db_matches,
            matched_business_rules=business_rule_matches,
            matched_automation_tests=automation_matches,
            matched_known_defects=defect_matches,
            matched_test_history=test_history_matches,
            risk_areas=risk_areas,
            source_files_loaded=source_files_loaded,
            retrieval_confidence=retrieval_confidence,
            open_context_questions=open_questions,
        )

        logger.info(
            "context retrieval completed confidence=%s feature_matches=%s api_matches=%s ui_matches=%s defects=%s",
            packet.retrieval_confidence,
            len(packet.matched_features),
            len(packet.matched_api_endpoints),
            len(packet.matched_ui_screens),
            len(packet.matched_known_defects),
        )
        logger.info(
            "context retrieval artifacts path=%s confidence=%s matched_features=%s total_matches=%s",
            manifest_path.as_posix(),
            packet.retrieval_confidence,
            len(packet.matched_features),
            self._count_total_matches(packet),
        )
        return packet

    def _empty_packet(self, question: str) -> RetrievedContextPacket:
        return RetrievedContextPacket(
            retrieval_confidence="low",
            open_context_questions=[question],
        )

    def _normalize_request_text(self, request: ContextRetrievalRequest) -> str:
        context_text = json.dumps(request.context, sort_keys=True)
        return f"{request.feature_description} {request.mode} {context_text}".lower()

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in TOKEN_PATTERN.findall(text.lower()) if len(token) > 1}

    def _load_json_file(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_supporting_collections(
        self,
        root_path: Path,
        manifest: dict[str, Any],
        source_files_loaded: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        collections: dict[str, list[dict[str, Any]]] = {}
        supporting_files = manifest.get("supporting_files", {})
        if not isinstance(supporting_files, dict):
            supporting_files = {}

        for collection_name in (
            "features",
            "ui_screens",
            "api_endpoints",
            "database_tables",
            "business_rules",
            "automation_tests",
            "known_defects",
            "test_history",
        ):
            if isinstance(manifest.get(collection_name), list):
                collections[collection_name] = self._coerce_collection_items(
                    manifest.get(collection_name, []),
                    fallback_source="knowledge/system-manifest.json",
                )
                continue

            referenced_path = supporting_files.get(collection_name)
            if not referenced_path:
                continue

            absolute_path = root_path / Path(str(referenced_path))
            if not absolute_path.exists():
                logger.info(
                    "context retrieval supporting file missing collection=%s path=%s",
                    collection_name,
                    absolute_path.as_posix(),
                )
                continue

            try:
                loaded = self._load_json_file(absolute_path)
            except (OSError, json.JSONDecodeError):
                logger.info(
                    "context retrieval supporting file unreadable collection=%s path=%s",
                    collection_name,
                    absolute_path.as_posix(),
                )
                continue

            source_files_loaded.append(absolute_path.as_posix())
            collections[collection_name] = self._coerce_collection_items(
                loaded,
                fallback_source=str(referenced_path).replace("\\", "/"),
            )

        return collections

    def _coerce_collection_items(self, payload: Any, fallback_source: str) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            for key in ("items", "features", "ui_screens", "api_endpoints", "database_tables", "business_rules", "automation_tests", "known_defects", "test_history"):
                if isinstance(payload.get(key), list):
                    payload = payload[key]
                    break

        if not isinstance(payload, list):
            return []

        items: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            normalized_item = dict(item)
            normalized_item.setdefault("source_file", fallback_source)
            items.append(normalized_item)
        return items

    def _build_feature_records(
        self,
        manifest: dict[str, Any],
        supporting_collections: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        feature_items = supporting_collections.get("features")
        if feature_items:
            return self._build_records_from_collection(
                feature_items,
                default_name_fields=("name", "feature_name"),
                artifact_type="feature",
            )
        return self._build_records_from_collection(
            self._coerce_collection_items(manifest.get("features", []), "knowledge/system-manifest.json"),
            default_name_fields=("name", "feature_name"),
            artifact_type="feature",
        )

    def _build_records_from_collection(
        self,
        collection: list[dict[str, Any]] | None,
        *,
        default_name_fields: tuple[str, ...],
        artifact_type: str,
    ) -> list[dict[str, Any]]:
        if not collection:
            return []

        records: list[dict[str, Any]] = []
        for item in collection:
            record = dict(item)
            record.setdefault("artifact_type", artifact_type)
            record["_name"] = self._resolve_name(item, default_name_fields)
            record["_aliases"] = self._coerce_str_list(item.get("aliases"))
            records.append(record)
        return records

    def _resolve_name(self, item: dict[str, Any], default_name_fields: tuple[str, ...]) -> str:
        for field_name in default_name_fields:
            value = item.get(field_name)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return str(item.get("id", "unknown"))

    def _coerce_str_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _match_items(
        self,
        *,
        request_tokens: set[str],
        items: list[dict[str, Any]],
        artifact_type: str,
        linked_ids: set[str] | None = None,
    ) -> list[MatchedContextItem]:
        linked_ids = linked_ids or set()
        matched: list[tuple[int, MatchedContextItem]] = []

        for item in items:
            item_id = str(item.get("id") or item.get("_name") or "unknown")
            item_name = str(item.get("_name") or item.get("name") or item.get("title") or item_id)
            item_path = str(item.get("path") or item.get("endpoint") or "")
            keywords = self._collect_keywords(item_name, item)
            overlap = sorted(request_tokens & keywords)
            is_linked = item_id in linked_ids or item_name in linked_ids or item_path in linked_ids

            if not overlap and not is_linked:
                continue

            score = len(overlap) + (2 if is_linked else 0)
            confidence = "high" if score >= 4 else "medium" if score >= 2 else "low"
            if is_linked and confidence == "low":
                confidence = "medium"

            reason_parts: list[str] = []
            if overlap:
                reason_parts.append(f"Matched request keywords: {', '.join(overlap[:5])}.")
            if is_linked:
                reason_parts.append("Linked from a matched feature artifact.")

            matched.append(
                (
                    score,
                    MatchedContextItem(
                        id=item_id,
                        name=item_name,
                        reason_matched=" ".join(reason_parts),
                        source_file=str(item.get("source_file", "")),
                        confidence=confidence,
                    ),
                )
            )

        matched.sort(key=lambda item: (-item[0], item[1].name.lower()))
        return [item[1] for item in matched]

    def _collect_keywords(self, item_name: str, item: dict[str, Any]) -> set[str]:
        keyword_sources = [item_name]
        keyword_sources.extend(self._coerce_str_list(item.get("aliases")))
        keyword_sources.extend(self._coerce_str_list(item.get("synonyms")))
        keyword_sources.extend(self._coerce_str_list(item.get("keywords")))
        for field_name in ("path", "endpoint", "table_name", "title", "rule_name", "screen_name"):
            value = item.get(field_name)
            if isinstance(value, str):
                keyword_sources.append(value)
        return self._tokenize(" ".join(keyword_sources))

    def _collect_linked_ids(
        self,
        feature_matches: list[MatchedContextItem],
        feature_records: list[dict[str, Any]],
    ) -> dict[str, set[str]]:
        linked: dict[str, set[str]] = {
            "ui_screen": set(),
            "api_endpoint": set(),
            "database_table": set(),
            "business_rule": set(),
            "automation_test": set(),
            "known_defect": set(),
            "test_history": set(),
        }
        feature_map = {
            str(item.get("id") or item.get("_name") or ""): item
            for item in feature_records
        }

        for feature in feature_matches:
            source_feature = feature_map.get(feature.id, {})
            linked["ui_screen"].update(self._coerce_str_list(source_feature.get("ui_screens")))
            linked["api_endpoint"].update(self._coerce_str_list(source_feature.get("api_endpoints")))
            linked["database_table"].update(self._coerce_str_list(source_feature.get("database_tables")))
            linked["business_rule"].update(self._coerce_str_list(source_feature.get("business_rules")))
            linked["automation_test"].update(self._coerce_str_list(source_feature.get("automation_tests")))
            linked["known_defect"].update(self._coerce_str_list(source_feature.get("known_defects")))
            linked["test_history"].update(self._coerce_str_list(source_feature.get("test_history")))

        return linked

    def _build_open_questions(
        self,
        *match_sets: list[MatchedContextItem],
    ) -> list[str]:
        if any(match_sets):
            return []
        return ["No PolicySphere artifacts matched strongly enough. Clarify feature terminology or provide more system context."]

    def _derive_confidence(self, *match_sets: list[MatchedContextItem]) -> str:
        total_matches = sum(len(match_set) for match_set in match_sets)
        if total_matches >= 6:
            return "high"
        if total_matches >= 2:
            return "medium"
        return "low"

    def _collect_risk_areas(
        self,
        feature_matches: list[MatchedContextItem],
        feature_records: list[dict[str, Any]],
    ) -> list[str]:
        feature_map = {str(item.get("id") or item.get("_name") or ""): item for item in feature_records}
        risk_areas: list[str] = []
        seen: set[str] = set()

        for feature in feature_matches:
            source_feature = feature_map.get(feature.id, {})
            for risk in self._coerce_str_list(source_feature.get("risk_areas")):
                normalized = risk.lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                risk_areas.append(risk)

        return risk_areas

    def _count_total_matches(self, packet: RetrievedContextPacket) -> int:
        return sum(
            len(match_set)
            for match_set in (
                packet.matched_features,
                packet.matched_ui_screens,
                packet.matched_api_endpoints,
                packet.matched_database_tables,
                packet.matched_business_rules,
                packet.matched_automation_tests,
                packet.matched_known_defects,
                packet.matched_test_history,
            )
        )

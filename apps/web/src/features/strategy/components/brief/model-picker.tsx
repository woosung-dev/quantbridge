"use client";

// provider 별 **살아 있는** 모델을 골라 그 모델로 해설을 만든다.
//
// ★★이 목록은 「고를 수 있는 후보」지 **「동작 보증」이 아니다.** 2026-08-28 실측이 그 경계를
//   그었다 — `gemini-3.7-flash` 는 목록에 **있는데** 503 을 내고, OpenAI 목록에는 capability
//   필드가 **없어서** chat 가능 여부를 서버가 이름으로 추측한다. 그래서 화면도 「쓸 수 있는
//   모델」이 아니라 「provider 가 목록에 올린 것」이라고 말한다.
// ★provider 하나가 죽어도 나머지는 고를 수 있다 — 실패는 그 provider 줄에만 표시된다.

import { useLlmModels } from "@/features/strategy/hooks";
import { LLM_PROVIDER_LABEL, type ModelChoice } from "@/features/strategy/schemas";

const DEFAULT_VALUE = "__default__";

function encode(provider: string, model: string): string {
  return `${provider} ${model}`;
}

export function ModelPicker({
  enabled,
  value,
  onChange,
}: {
  enabled: boolean;
  value: ModelChoice;
  onChange: (next: ModelChoice) => void;
}) {
  const query = useLlmModels(enabled);
  const data = query.data ?? null;

  // ★목록을 못 읽었다고 고르기 UI 를 **없애지 않는다** — 없애면 왜 사라졌는지 알 수 없다.
  //   대신 비활성 + 사유를 적는다.
  const disabled = !data || query.isPending || query.isError;

  return (
    <div className="field-inline" data-testid="model-picker">
      <label className="field-label" htmlFor="narrative-model">
        모델
      </label>
      <select
        id="narrative-model"
        className="select select-xs"
        data-testid="model-picker-select"
        disabled={disabled}
        value={value ? encode(value.provider, value.model) : DEFAULT_VALUE}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === DEFAULT_VALUE) {
            onChange(null);
            return;
          }
          // ★`noUncheckedIndexedAccess` 라 구조분해는 `string | undefined` 다. 값은 우리가
          //   `encode` 로 만든 것뿐이지만, 그 사실에 기대지 않고 형태를 확인하고 넘긴다.
          const sep = raw.indexOf(" ");
          if (sep <= 0 || sep === raw.length - 1) {
            onChange(null);
            return;
          }
          onChange({ provider: raw.slice(0, sep), model: raw.slice(sep + 1) });
        }}
      >
        <option value={DEFAULT_VALUE}>
          기본 설정{data?.active ? ` · ${LLM_PROVIDER_LABEL[data.active] ?? data.active}` : ""}
        </option>
        {(data?.providers ?? [])
          .filter((p) => p.models.length > 0)
          .map((p) => (
            <optgroup key={p.provider} label={LLM_PROVIDER_LABEL[p.provider] ?? p.provider}>
              {p.models.map((m) => (
                <option key={`${p.provider}:${m.id}`} value={encode(p.provider, m.id)}>
                  {m.display_name ?? m.id}
                  {m.shutdown_date ? ` (종료 ${m.shutdown_date})` : ""}
                </option>
              ))}
            </optgroup>
          ))}
      </select>

      {query.isPending && enabled ? (
        <span className="field-hint" data-testid="model-picker-loading">
          모델 목록을 읽는 중입니다.
        </span>
      ) : null}

      {query.isError ? (
        <span className="field-hint" data-testid="model-picker-error">
          모델 목록을 읽지 못했습니다. 기본 설정으로 해설을 만듭니다.
        </span>
      ) : null}

      {/* ★설정된 모델이 provider 목록에 **없으면** 말한다. 이 한 줄이 오늘 고친 결함
          (gemini-2.0-flash 폐기 → 404)을 화면에서 보이게 하는 자리다.
          ★configured_listed 는 3값이다 — null 은 「없다」가 아니라 「목록을 못 읽어 모른다」라
            아무 말도 하지 않는다. 모르는 것을 경고로 바꾸면 멀쩡한 설정이 빨갛게 보인다. */}
      {(data?.providers ?? [])
        .filter((p) => p.configured_listed === false)
        .map((p) => (
          <span key={p.provider} className="field-hint" data-testid="model-picker-drift">
            설정된 {LLM_PROVIDER_LABEL[p.provider] ?? p.provider} 모델 {p.configured} 이(가)
            provider 목록에 없습니다 · 폐기됐을 수 있습니다
          </span>
        ))}
    </div>
  );
}

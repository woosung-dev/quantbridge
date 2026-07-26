---
description: Flutter, Dart 스택 및 Mobile 규칙
paths:
  - "mobile/**/*"
---

# Flutter Rules (Feature-First + Riverpod + Repository)

Feature-First 폴더 구조 안에 presentation / data 레이어를 두며,
Riverpod로 상태를 관리하고 Repository 패턴으로 데이터를 추상화한다.
**모든 기능은 아래 구조를 동일하게 따른다.**

---

## 1. 아키텍처 개요

```
features/{feature}/
├── presentation/
│   ├── screens/          # Screen Widget (UI만 담당)
│   ├── widgets/          # 재사용 Widget
│   └── providers/        # Riverpod Notifier + Provider 선언
├── domain/               # 선택적 — 복잡한 조합 로직이 있을 때만 추가
│   └── usecases/
└── data/
    ├── repositories/     # 인터페이스 + 구현체 분리
    └── models/           # freezed + json_serializable
```

### 핵심 원칙

- Repository는 **인터페이스와 구현체를 분리**한다
- `domain/usecases/`는 기본 없음. **사용자가 명시적으로 요청할 때만** 추가한다.
- 기본은 **단일 모델**. API 응답 구조와 앱 내부 모델이 **달라지는 시점**에 DTO/Entity를 분리한다.
- `freezed` + `json_serializable` 필수

---

## 2. 공통 폴더 구조

```
lib/
├── features/             # 도메인별 기능 모듈
│   └── {feature}/
├── core/
│   ├── router/           # go_router 설정
│   ├── network/          # Dio 클라이언트, 인터셉터
│   ├── error/            # 전역 에러 타입 (Failure 클래스)
│   └── di/               # Riverpod Provider 전역 override
└── main.dart
```

- 기능 간 참조는 `core/`를 통하거나 해당 feature의 public export를 통해서만 한다
- 다른 feature의 내부 파일을 직접 import 금지

---

## 3. 레이어 규칙

### Widget (presentation/screens, widgets)

- UI 렌더링과 사용자 입력 전달만 담당. Widget을 멍청하게(Dumb) 유지.
- 비즈니스 로직, API 호출, 조건 계산을 Widget 안에 작성 금지.
- `ConsumerWidget` 또는 `ConsumerStatefulWidget` 사용.
- `build()` 안에서는 `ref.watch()` 필수. `ref.read()` 사용 금지.
- 이벤트 핸들러 안에서는 `ref.read()` 필수. `ref.watch()` 사용 금지.

### Notifier (presentation/providers)

- UI와 Repository 사이의 조율(Orchestration) 담당.
- `AsyncNotifier` 또는 `Notifier` 사용. `StateNotifier` 사용 금지 (구버전).
- Repository를 `ref.read()`로 주입받아 사용.
- 에러는 `AsyncValue.error()`로 처리. try-catch 직접 노출 금지.

### Repository (data/repositories)

- 데이터 접근을 추상화. API 호출, 데이터 변환, 파싱 모두 여기서 처리.
- **인터페이스(`abstract class`)와 구현체를 반드시 분리.**
- 반환 타입은 `Future<T>` 통일. DTO/Entity 분리 시 Entity를 반환.

### Model (data/models)

- `freezed` + `json_serializable` 필수.
- **기본: 단일 모델 클래스** (DTO와 Entity를 겸함). 새 기능은 항상 단일 모델로 시작.
- **분리 트리거:** API 응답 필드와 앱 내부 모델이 달라지는 시점에 DTO/Entity를 분리한다.
  - 예: API는 `created_at` (String) → 앱은 `createdAt` (DateTime) 변환이 복잡해질 때
  - 분리 시: DTO는 API 전용, Entity는 앱 내부용.
  - Entity에 `fromJson` 작성 금지 → DTO에서만 `fromJson` 허용.
  - DTO → Entity 변환은 Repository 구현체 안에서 처리.

---

## 4. 필수 코드 패턴

### Repository 인터페이스 + 구현체

```dart
// ✅ 인터페이스
abstract class OrderRepository {
  Future<List<Order>> getOrders();
  Future<Order> createOrder(CreateOrderDto dto);
}

// ✅ 구현체
class OrderRepositoryImpl implements OrderRepository {
  OrderRepositoryImpl(this._remote);
  final OrderRemoteDataSource _remote;

  @override
  Future<List<Order>> getOrders() async {
    final dtos = await _remote.fetchOrders();
    return dtos.map((e) => e.toEntity()).toList();
  }
}
```

### Riverpod AsyncNotifier

```dart
@riverpod
class OrdersNotifier extends _$OrdersNotifier {
  @override
  Future<List<Order>> build() async {
    return ref.read(orderRepositoryProvider).getOrders();
  }

  Future<void> createOrder(CreateOrderDto dto) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(orderRepositoryProvider).createOrder(dto),
    );
  }
}
```

### Provider 선언 (Riverpod Generator)

```dart
@riverpod
OrderRepository orderRepository(OrderRepositoryRef ref) {
  return OrderRepositoryImpl(ref.read(orderRemoteDataSourceProvider));
}
```

### ConsumerWidget

```dart
// ✅ build()에서 watch, 이벤트에서 read
class OrdersScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ordersAsync = ref.watch(ordersNotifierProvider);

    return ordersAsync.when(
      data: (orders) => OrdersList(orders: orders),
      loading: () => const CircularProgressIndicator(),
      error: (e, _) => ErrorView(message: e.toString()),
    );
  }
}

class CreateOrderButton extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ElevatedButton(
      onPressed: () {
        ref.read(ordersNotifierProvider.notifier).createOrder(dto);
      },
      child: const Text('주문하기'),
    );
  }
}
```

### Model (freezed)

```dart
// ✅ freezed 필수
@freezed
class Order with _$Order {
  const factory Order({
    required String id,
    required int amount,
    @JsonKey(name: 'created_at') required DateTime createdAt,
  }) = _Order;

  factory Order.fromJson(Map<String, dynamic> json) =>
      _$OrderFromJson(json);
}
```

### DTO/Entity 분리가 필요한 경우 (선택적)

```dart
// DTO — API 전용
@freezed
class OrderDto with _$OrderDto {
  const factory OrderDto({
    required String id,
    required int amount,
    @JsonKey(name: 'created_at') required String createdAt,
  }) = _OrderDto;

  factory OrderDto.fromJson(Map<String, dynamic> json) =>
      _$OrderDtoFromJson(json);
}

// Entity — 앱 내부용. fromJson 금지.
@freezed
class Order with _$Order {
  const factory Order({
    required String id,
    required int amount,
    required DateTime createdAt,
  }) = _Order;
}
```

---

## 5. 라우팅 규칙

- `go_router`만 사용. `Navigator.push` / `Navigator.pushNamed` 사용 금지.
- 라우트는 `core/router/`에서만 선언. 각 feature 안에 라우트 선언 금지.
- 타입 안전 라우팅을 위해 `GoRoute`의 path + typed route 패턴 사용.

---

## 6. 네이밍 규칙

- 직관적인 이름만 사용
- 금지: `BaseUseCase`, `Manager`, `Handler` 등 과도한 추상화 네이밍
- Provider 이름: `{feature}Provider` (예: `ordersNotifierProvider`)
- Repository: `{Feature}Repository` / `{Feature}RepositoryImpl`

---

## 7. 엄격 금지 사항

- `StateNotifier` 사용 금지 → `AsyncNotifier` / `Notifier` 사용
- `Navigator.push` 사용 금지 → `context.go()` / `context.push()` 사용
- `build()` 안에서 `ref.read()` 사용 금지 → `ref.watch()` 사용
- 이벤트 핸들러 안에서 `ref.watch()` 사용 금지 → `ref.read()` 사용
- Entity에 `fromJson` 작성 금지 (분리 시) → DTO에서만 `fromJson` 허용
- `freezed` 없이 `copyWith` 수동 작성 금지
- 다른 feature 내부 파일 직접 import 금지
- `domain/usecases/` 자의적 추가 금지 → 사용자가 명시적으로 요청할 때만
- DTO/Entity 선제 분리 금지 → 단일 모델로 시작, 분리 트리거 충족 시에만
- 아키텍처 구조 변경(DTO/Entity 분리, DataSource 추가 등)은 팀 합의 후 진행

---

## 참고: 확장 트리거

아래 조건이 충족될 때만 구조를 확장한다. 사전 확장 금지.

| 확장                | 트리거 조건                                  |
| ------------------- | -------------------------------------------- |
| **DTO/Entity 분리** | API 응답 구조와 앱 내부 모델이 달라지는 시점 |
| **DataSource 계층** | Remote/Local 캐싱이 필요해진 시점            |
| **UseCase**         | 사용자가 명시적으로 요청한 시점              |

확장 시 폴더 구조:

```
features/{feature}/
├── presentation/
├── domain/
│   ├── entities/         # 앱 내부용 순수 모델
│   └── usecases/
└── data/
    ├── repositories/     # interface + impl
    ├── models/           # API 전용 DTO
    └── data_sources/     # Remote / Local
```

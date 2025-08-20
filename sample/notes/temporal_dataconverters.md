# Temporal Data Converters: When and How to Use Them

## Overview

Temporal's Data Converters handle serialization and encoding of data entering and exiting a Temporal Service. Most of the time, you don't need to think about them at all—Temporal's defaults work great. But knowing when and how to customize them can solve specific problems and unlock powerful capabilities.

---

## Architectural Placement in Our Project

**In this project, we follow the principles outlined in `GUIDE.md`. This means all framework-specific configuration must live in the outermost "Interface Adapters" layer.**

The `DataConverter` is a prime example of a framework-specific concern. It dictates how the `temporalio` library communicates with the Temporal service. Therefore, it must be configured at the boundary of our application, where the framework is initialized.

-   **Client-Side Configuration**: In `sample/api/app.py`, the `get_temporal_client()` function configures the `DataConverter`. This ensures any data sent *to* a workflow (like a `CreateOrderRequest`) is correctly serialized before it leaves our application.
-   **Worker-Side Configuration**: In `sample/worker.py`, the `Worker` is initialized with a `Client` that has been configured with the exact same `DataConverter`. This ensures any data received *from* Temporal is correctly deserialized before being passed to our workflow code.

This approach is critical for maintaining architectural integrity:
-   ✅ **It respects the Dependency Rule**: The `usecase` and `domain` layers remain completely unaware of how Temporal serializes data.
-   ❌ **Anti-Pattern**: Attempting to configure serialization inside a repository or use case would violate the architecture by making the core business logic dependent on a framework detail.

By keeping this configuration at the edge, we ensure our core logic is portable, testable, and independent of the underlying workflow engine.

---

## Decision Matrix: When to Intervene

### 🟢 **Let Temporal Handle It (Default Behavior)**

**When the defaults work perfectly:**

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class UserPreferences:
    user_id: str
    theme: str
    notifications_enabled: bool
    last_login: Optional[datetime]
    tags: List[str]

@workflow.defn
class UserWorkflow:
    @workflow.run
    async def run(self, prefs: UserPreferences) -> str:
        # Temporal handles serialization automatically
        return f"Updated preferences for {prefs.user_id}"
```

**Default support includes:**
- All Python primitives (`str`, `int`, `float`, `bool`)
- Standard collections (`list`, `dict`, `set`, `tuple`)
- Common types (`datetime`, `UUID`, `Decimal`)
- Dataclasses with proper type hints
- Optional and Union types
- Protobuf messages
- JSON-serializable objects

**✅ Stick with defaults when:**
- Using standard Python types
- Working with simple dataclasses
- Prototyping or getting started
- No security/compliance requirements
- No performance constraints
- No interoperability concerns

### 🟡 **Give Temporal Hints (Type Annotations & Simple Config)**

**When you need basic guidance:**

```python
from typing import NewType, List
from datetime import datetime

# Custom type hints help Temporal understand your intent
UserId = NewType('UserId', str)
Timestamp = NewType('Timestamp', datetime)

@dataclass
class Event:
    user_id: UserId  # Clear semantic meaning
    timestamp: Timestamp
    event_type: str
    metadata: dict[str, any]  # Temporal handles nested JSON

@workflow.defn
class EventProcessor:
    @workflow.run
    async def run(self, events: List[Event]) -> dict[UserId, int]:
        # Type hints guide serialization and IDE support
        return {event.user_id: len(events) for event in events}
```

**🔧 Simple Pydantic Integration:**
```python
# Use the built-in Pydantic converter for validation
from temporalio.contrib.pydantic import PydanticPayloadConverter
import dataclasses

pydantic_converter = dataclasses.replace(
    DataConverter.default,
    payload_converter_class=PydanticPayloadConverter,
)
```

**⚠️ Give hints when:**
- Using complex nested structures
- Want validation (Pydantic models)
- Need semantic clarity (NewType)
- Working with team members
- Building long-term systems

### 🔴 **Take Full Control (Custom Data Converters)**

**When defaults aren't enough:**

#### **Scenario 1: Non-Serializable Types**

```python
import ipaddress
from temporalio.converter import EncodingPayloadConverter, CompositePayloadConverter

class IPv4AddressConverter(EncodingPayloadConverter):
    @property
    def encoding(self) -> str:
        return "text/ipv4-address"
    
    def to_payload(self, value: any) -> Optional[Payload]:
        if isinstance(value, ipaddress.IPv4Address):
            return Payload(
                metadata={"encoding": self.encoding.encode()},
                data=str(value).encode(),
            )
        return None
    
    def from_payload(self, payload: Payload, type_hint: Optional[Type] = None) -> any:
        return ipaddress.IPv4Address(payload.data.decode())

# Custom types require custom converters
@dataclass
class NetworkConfig:
    server_ip: ipaddress.IPv4Address  # Won't work with defaults
    allowed_ranges: List[ipaddress.IPv4Network]
```

#### **Scenario 2: Security Requirements**

```python
from temporalio.converter import PayloadCodec
import cryptography.fernet

class EncryptionCodec(PayloadCodec):
    def __init__(self, key: bytes):
        self.fernet = cryptography.fernet.Fernet(key)
    
    async def encode(self, payloads: Iterable[Payload]) -> List[Payload]:
        result = []
        for payload in payloads:
            # Encrypt sensitive data before sending to Temporal
            encrypted_data = self.fernet.encrypt(payload.data)
            result.append(Payload(
                metadata={**payload.metadata, "encoding": b"binary/encrypted"},
                data=encrypted_data
            ))
        return result
    
    async def decode(self, payloads: Iterable[Payload]) -> List[Payload]:
        # Decrypt when receiving from Temporal
        result = []
        for payload in payloads:
            if payload.metadata.get("encoding") == b"binary/encrypted":
                decrypted_data = self.fernet.decrypt(payload.data)
                result.append(Payload(
                    metadata={k: v for k, v in payload.metadata.items() if k != "encoding"},
                    data=decrypted_data
                ))
            else:
                result.append(payload)
        return result
```

#### **Scenario 3: Performance Optimization**

```python
class CompressionCodec(PayloadCodec):
    async def encode(self, payloads: Iterable[Payload]) -> List[Payload]:
        result = []
        for payload in payloads:
            # Compress large payloads
            if len(payload.data) > 10_000:  # 10KB threshold
                compressed = gzip.compress(payload.data)
                result.append(Payload(
                    metadata={**payload.metadata, "encoding": b"binary/gzip"},
                    data=compressed
                ))
            else:
                result.append(payload)
        return result
```

#### **Scenario 4: External Storage**

```python
class S3StorageConverter(EncodingPayloadConverter):
    @property 
    def encoding(self) -> str:
        return "reference/s3"
    
    def to_payload(self, value: any) -> Optional[Payload]:
        # Store large objects in S3, return reference
        if isinstance(value, LargeDataset) and len(value.data) > 1_000_000:
            s3_key = self.upload_to_s3(value)
            return Payload(
                metadata={"encoding": self.encoding.encode()},
                data=s3_key.encode(),
            )
        return None
    
    def from_payload(self, payload: Payload, type_hint: Optional[Type] = None) -> any:
        s3_key = payload.data.decode()
        return self.download_from_s3(s3_key)
```

**🚨 Take control when:**
- **Security**: Encrypting sensitive data
- **Compliance**: Meeting regulatory requirements  
- **Performance**: Large payloads need compression
- **Custom Types**: Non-JSON-serializable objects
- **External Storage**: Payloads exceed size limits
- **Interoperability**: Working with other systems/languages
- **Legacy Integration**: Existing serialization formats

## Implementation Patterns

### Pattern 1: Additive Custom Types

```python
class MyCompositeConverter(CompositePayloadConverter):
    def __init__(self) -> None:
        super().__init__(
            # Add your custom converters first
            IPv4AddressConverter(),
            CustomDateTimeConverter(),
            # Keep all the defaults as fallback
            *DefaultPayloadConverter.default_encoding_payload_converters,
        )
```

### Pattern 2: Enhanced JSON Conversion

```python
class EnhancedJSONConverter(CompositePayloadConverter):
    def __init__(self) -> None:
        # Replace the default JSON converter with enhanced version
        enhanced_json = JSONPlainPayloadConverter(
            encoder=MyCustomJSONEncoder,
            custom_type_converters=[MyTypeConverter()],
        )
        
        super().__init__(
            *[
                c if not isinstance(c, JSONPlainPayloadConverter) else enhanced_json
                for c in DefaultPayloadConverter.default_encoding_payload_converters
            ]
        )
```

### Pattern 3: Layered Security

```python
# Combine payload conversion + encryption
secure_converter = dataclasses.replace(
    DataConverter.default,
    payload_converter_class=MyCustomConverter,
    payload_codec=EncryptionCodec(encryption_key),
)
```

## Configuration Best Practices

### Client and Worker Consistency

The `DataConverter` is configured on the `Client` and is automatically used by any `Worker` created with that client. It's critical that both the client starting the workflow and the worker executing it are configured with compatible data converters.

```python
# The data converter is configured on the client
my_converter = dataclasses.replace(
    DataConverter.default,
    payload_converter_class=MyCustomConverter,
)

# Client configuration
client = await Client.connect(
    "localhost:7233",
    data_converter=my_converter,
)

# Worker configuration  
# The worker will automatically use the data converter from the client.
worker = Worker(
    client,
    task_queue="my-queue",
    workflows=[MyWorkflow],
    activities=[my_activity],
)
```

### Environment-Based Configuration

```python
def create_data_converter(environment: str) -> DataConverter:
    if environment == "production":
        return dataclasses.replace(
            DataConverter.default,
            payload_converter_class=SecureConverter,
            payload_codec=EncryptionCodec(get_production_key()),
        )
    elif environment == "development":
        return dataclasses.replace(
            DataConverter.default,
            payload_converter_class=EnhancedConverter,
        )
    else:
        # Use defaults for testing
        return DataConverter.default
```

## Testing Strategy

### Unit Testing Custom Converters

```python
@pytest.mark.asyncio
async def test_custom_converter():
    converter = DataConverter(payload_converter_class=MyConverter)
    
    # Test round-trip conversion
    original = MyCustomObject(value="test")
    payloads = await converter.encode([original])
    decoded = await converter.decode(payloads, [MyCustomObject])
    
    assert decoded[0] == original

@pytest.mark.asyncio 
async def test_fallback_behavior():
    converter = MyCompositeConverter()
    
    # Ensure standard types still work
    standard_obj = {"key": "value", "count": 42}
    payloads = await converter.encode([standard_obj])
    decoded = await converter.decode(payloads, [dict])
    
    assert decoded[0] == standard_obj
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_workflow_with_custom_converter():
    client = await Client.connect(
        "localhost:7233",
        data_converter=my_converter,
    )
    
    # Test actual workflow execution
    result = await client.execute_workflow(
        MyWorkflow.run,
        MyCustomInput(data="test"),
        id="test-workflow",
        task_queue="test-queue",
    )
    
    assert isinstance(result, MyCustomOutput)
```

## Common Pitfalls and Solutions

### ❌ **Pitfall 1: Inconsistent Converters**
```python
# DON'T: Different converters for client and worker
client = Client.connect(data_converter=ConverterA())
worker_client = Client.connect(data_converter=ConverterB()) # WRONG!
worker = Worker(client=worker_client)
```

### ✅ **Solution: Shared Configuration**
```python
# DO: Share the same converter instance or configuration
shared_converter = create_converter()
client = Client.connect(data_converter=shared_converter)
worker_client = Client.connect(data_converter=shared_converter)
worker = Worker(client=worker_client)
```

### ❌ **Pitfall 2: Breaking Changes**
```python
# DON'T: Change encoding names or formats
class BadConverter(EncodingPayloadConverter):
    def encoding(self) -> str:
        return "v2/my-format"  # Changed from "v1/my-format" - breaks existing data!
```

### ✅ **Solution: Versioned Converters** 
```python
class VersionedConverter(EncodingPayloadConverter):
    def from_payload(self, payload: Payload, type_hint: Optional[Type] = None) -> any:
        encoding = payload.metadata.get("encoding", b"").decode()
        if encoding == "v1/my-format":
            return self.decode_v1(payload)
        elif encoding == "v2/my-format":
            return self.decode_v2(payload)
        else:
            raise ValueError(f"Unsupported encoding: {encoding}")
```

### ❌ **Pitfall 3: Silent Failures**
```python
def to_payload(self, value: any) -> Optional[Payload]:
    try:
        return self.serialize(value)
    except:
        return None  # Silent failure - hard to debug!
```

### ✅ **Solution: Explicit Error Handling**
```python
def to_payload(self, value: any) -> Optional[Payload]:
    if not self.can_handle(value):
        return None  # Explicit - let other converters try
    
    try:
        return self.serialize(value)
    except Exception as e:
        logger.error(f"Failed to serialize {type(value)}: {e}")
        raise  # Don't hide real errors
```

## Summary Decision Tree

```
Do you need custom serialization?
├─ No → Use Temporal defaults ✅
├─ Maybe → 
│   ├─ Need validation? → Use Pydantic converter 🟡
│   ├─ Complex types? → Add type hints 🟡
│   └─ Still works? → Stick with enhanced defaults 🟡
└─ Yes →
    ├─ Security required? → Custom codec + encryption 🔴
    ├─ Large payloads? → Compression or external storage 🔴
    ├─ Custom types? → Custom payload converter 🔴
    └─ Legacy formats? → Full custom implementation 🔴
```

**Start simple, evolve as needed.** Temporal's defaults handle 90% of use cases perfectly. Only add complexity when you have a specific problem to solve.

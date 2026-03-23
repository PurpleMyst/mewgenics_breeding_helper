---
name: imhex-pattern-language
description: >
  Expertise in writing, analyzing, and debugging the ImHex Pattern Language (.pat / .hexpat).
  Use this skill when tasked with parsing binary data, defining binary file format structures,
  reverse-engineering binary files, or writing scripts for the ImHex hex editor.
triggers:
  - "imhex"
  - "pattern language"
  - "hexpat"
  - "binary parsing"
  - ".pat file"
---

# ImHex Pattern Language (Hexpat) Guidelines

You are an expert in the ImHex Pattern Language. This language is a C-like domain-specific language (DSL) used within the ImHex hex editor to parse, highlight, and decode structured binary data. 

When writing or analyzing ImHex patterns, adhere strictly to the following language rules and structures.

## 1. Core Types and Variables
The language uses explicitly sized types to map directly to binary data.
* **Unsigned Integers:** `u8`, `u16`, `u24`, `u32`, `u64`, `u128`
* **Signed Integers:** `s8`, `s16`, `s32`, `s64`, `s128`
* **Floating Point:** `float` (32-bit), `double` (64-bit)
* **Characters:** `char`, `char16_t`
* **Boolean:** `bool`

Variables declared in the global scope without placement operators act as local script variables, not mapped data.

## 2. Structs and Placement (The `@` Operator)
Structs are the primary way to define complex data layouts. To map a struct to the actual binary data in the hex editor, use the placement operator (`@`).

```cpp
struct Header {
    u32 magic;
    u16 version;
    u16 flags;
};

// Place the Header struct exactly at offset 0x00
Header file_header @ 0x00;
```

**The Current Offset (`$`)**: You can use `$` to refer to the current offset during parsing.
```cpp
u32 dynamic_data @ $; 
```

## 3. Arrays
Arrays can be fixed-size or dynamically sized based on other parsed variables. ImHex handles them seamlessly.

```cpp
struct Section {
    u32 size;
    // Dynamically sized array based on the previously parsed 'size'
    u8 data[size]; 
};

Section sections[4] @ 0x10; // Fixed array of 4 sections starting at 0x10
```

*Note on 2D Arrays:* ImHex does not have native 2D arrays. To implement a 2D array, wrap a 1D array inside a struct, then create an array of that struct.

## 4. Bitfields
For data packed into sub-byte structures, use `bitfield`. The numbers represent the number of bits each field consumes.

```cpp
bitfield Permissions {
    read  : 1;
    write : 1;
    exec  : 1;
    pad   : 5; // Pad out to a full byte (8 bits)
};

Permissions file_perms @ 0x08;
```

## 5. Enums and Unions
* **Enums:** Map integer values to readable names. You can specify the underlying type.
  ```cpp
  enum ChunkType : u16 {
      Data = 0x0001,
      Header = 0x0002,
      Footer = 0xFFFF
  };
  ```
* **Unions:** Allow the same memory address to be interpreted in multiple ways simultaneously.

## 6. Pragmas
Pragmas define file-wide configurations and validations.
* `#pragma endian big` or `#pragma endian little`: Sets the default byte order.
* `#pragma magic [ "signature" @ offset ]`: Automatically checks if a file matches a signature. If the magic bytes don't match, ImHex aborts evaluating the pattern.
  ```cpp
  #pragma endian little
  #pragma magic [ 0x7F "ELF" @ 0x00 ]
  ```

## 7. Functions and Control Flow
ImHex allows functions for mathematical calculations or offset processing, as well as `if`, `while`, and `for` loops inside structs or functions.

```cpp
fn calculate_padding(u32 current_offset, u32 alignment) {
    return (alignment - (current_offset % alignment)) % alignment;
};

struct DynamicBlock {
    u8 type;
    if (type == 0x01) {
        u32 extended_data;
    }
};
```

## 8. Best Practices for the Agent
* **Context is Key:** Always verify the endianness of the file format before drafting a pattern.
* **Progressive Parsing:** Use previously declared struct members to dictate the size or existence of subsequent members.
* **Padding:** Account for byte-alignment in binary files. Use `padding[size];` to explicitly consume alignment bytes so the parser stays synchronized with the data.
* **Safety:** When writing patterns with loops (`while`), ensure there is a clear exit condition to prevent the ImHex engine from hanging.

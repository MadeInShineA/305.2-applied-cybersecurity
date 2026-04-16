#!/usr/bin/env nu
# Usage:
#   nu infomaniak-ai.nu "Hello"
#   nu infomaniak-ai.nu "Hello" --raw
 
def infomaniak-ai [
    message: string,
    model: string = "qwen3",
    raw: bool = false
] {
    # Load .env if credentials missing
    if ($env.INFOMANIAK_AI_KEY? == null) {
        open .env | from toml | load-env
    }

    # Make API request
    let response = (http post
        -t "application/json"
        -H { Authorization: $"Bearer ($env.INFOMANIAK_AI_KEY)" }
        $"https://api.infomaniak.com/2/ai/($env.INFOMANIAK_AI_PRODUCT_ID)/openai/v1/chat/completions"
        {
            messages: [[content, role]; [$message, "user"]]
            model: $model
        }
    )

    # Return just content by default, or full response if raw
    if $raw {
        $response
    } else {
        $response.choices.0.message.content | str trim
    }
}

export def main [
    message: string,
    model: string = "qwen3"
    --raw
] {
    try {
        infomaniak-ai $message $model $raw
    } catch {|e|
        print $"Error: ($e.msg)"
        exit 1
    }
}

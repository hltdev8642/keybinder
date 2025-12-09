function init()
    -- Initialize mod
end

function tick(dt)
    if InputPressed("Key_X") then
        -- Do something when X is pressed
        DebugPrint("X pressed")
    end

    if InputDown("Key_C") then
        -- Continuous action while C is held
        DebugPrint("C held")
    end

    if InputReleased("interact") then
        -- Interact released
        DebugPrint("Interact released")
    end

    -- Some other code
    local value = InputValue("mousewheel")
    if value > 0 then
        -- Scroll up
    end
end
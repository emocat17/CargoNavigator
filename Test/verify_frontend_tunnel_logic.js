// Test script to verify frontend logic for tunnel detection
// This mimics the logic in RouteResultPanel.vue

const isTunnel = (step) => {
    if (!step) return false;
    const road = step.road || '';
    const instruction = step.instruction || '';
    const action = step.assistant_action || '';
    return road.includes('隧道') || instruction.includes('隧道') || action.includes('隧道');
}

const isLongTunnel = (step) => {
    return isTunnel(step) && step.distance > 3000;
}

// Test Cases
const steps = [
    { name: "Normal Road", road: "G5", instruction: "Go straight", distance: 5000, assistant_action: "" },
    { name: "Short Tunnel", road: "小隧道", instruction: "Enter tunnel", distance: 1000, assistant_action: "" },
    { name: "Long Tunnel", road: "大山隧道", instruction: "Enter tunnel", distance: 5000, assistant_action: "" },
    { name: "Tunnel via Instruction", road: "G5", instruction: "Enter Qinling 隧道", distance: 200, assistant_action: "" },
    { name: "Long Tunnel via Action", road: "G5", instruction: "Go", distance: 4000, assistant_action: "进入隧道" }
];

console.log("Running Frontend Tunnel Logic Verification...");
let passed = 0;
let total = 0;

function assert(condition, msg) {
    total++;
    if (condition) {
        passed++;
        console.log(`[PASS] ${msg}`);
    } else {
        console.error(`[FAIL] ${msg}`);
    }
}

// Case 1: Normal Road
assert(isTunnel(steps[0]) === false, "Normal road should not be tunnel");

// Case 2: Short Tunnel
assert(isTunnel(steps[1]) === true, "Short Tunnel should be detected");
assert(isLongTunnel(steps[1]) === false, "Short Tunnel should NOT be long");

// Case 3: Long Tunnel
assert(isTunnel(steps[2]) === true, "Long Tunnel should be detected");
assert(isLongTunnel(steps[2]) === true, "Long Tunnel should be long (>3000m)");

// Case 4: Tunnel via Instruction
assert(isTunnel(steps[3]) === true, "Tunnel via instruction detected");

// Case 5: Long Tunnel via Action
assert(isTunnel(steps[4]) === true, "Tunnel via action detected");
assert(isLongTunnel(steps[4]) === true, "Long Tunnel via action detected");

console.log(`Result: ${passed}/${total} passed.`);

if (passed === total) {
    console.log("SUCCESS: All tunnel logic tests passed.");
    process.exit(0);
} else {
    console.log("FAILURE: Some tests failed.");
    process.exit(1);
}

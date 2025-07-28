from flask import Flask, jsonify, request
from datetime import datetime
import random
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)
pcs_data = []

def initialize_pcs():
    global pcs_data
    pcs_data = []
    
    for i in range(1, 21):
        if i <= 10:
            status = 'active'
        elif i <= 17:
            status = 'user'
        elif i <= 19:
            status = 'conflict'
        else:
            status = 'backup'

        pc = {
            'id': f'PC-{str(i).zfill(2)}',
            'status': status,
            'cpu': random.randint(20, 60),
            'ram': random.randint(30, 80),
            'disk': random.randint(15, 45),
            'last_updated': datetime.now().strftime('%H:%M:%S'),
            'position': i - 1, 
            'location': f'Row-{(i - 1) // 5 + 1}, Seat-{(i - 1) % 5 + 1}',
            # Perfectly aligned grid positioning
            'x': ((i - 1) % 5) * 5.0 - 10,  # Evenly spaced in rows (5 units apart)
            'y': 0,                          # Consistent height
            'z': -((i - 1) // 5) * 5.0 + 5, # Evenly spaced in columns (5 units apart)
            # Remove randomization for perfect alignment
            'size_variation': 1.0,           # Fixed size (no variation)
            'rotation_y': 0.0,               # No rotation (perfectly aligned)
            'conflict_type': 'hardware_conflict' if status == 'conflict' and random.random() > 0.5 else 'software_conflict' if status == 'conflict' else None,
            'remote_active': random.random() > 0.7 if status in ['user', 'active'] else False,
            'os_version': f"Windows {random.choice(['10', '11'])} Pro",
            'uptime': random.randint(1, 72)
        }
        pcs_data.append(pc)

initialize_pcs()

def emit_pc_update(pc_id=None):
    if pc_id:
        pc = next((p for p in pcs_data if p['id'] == pc_id), None)
        if pc:
            socketio.emit('pc_update', {'pc': pc})
    else:
        socketio.emit('pcs_refresh', {'pcs': pcs_data})


@app.route('/')
def replica_view():  
    return render_3d_template("Main 3D Lab", show_controls=False)

@app.route('/control')
def main_3d_view():  
    return render_3d_template("Control Panel - 3D Lab", show_controls=True)

def render_3d_template(title, show_controls):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{ margin: 0; overflow: hidden; font-family: Arial, sans-serif; }}
            #info {{
                position: absolute;
                top: 10px;
                width: 100%;
                text-align: center;
                color: white;
                background-color: rgba(0,0,0,0.7);
                padding: 10px;
                z-index: 100;
            }}
            #stats {{
                position: absolute;
                top: 60px;
                left: 10px;
                background-color: rgba(0,0,0,0.7);
                color: white;
                padding: 10px;
                border-radius: 5px;
                z-index: 100;
            }}
            #controls {{
                position: absolute;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background-color: rgba(0,0,0,0.7);
                color: white;
                padding: 10px;
                border-radius: 5px;
                z-index: 100;
                display: flex;
                gap: 10px;
                display: {'block' if show_controls else 'none'};
            }}
            button {{
                padding: 8px 15px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }}
            button:hover {{ background-color: #45a049; }}
            #pc-details {{
                position: absolute;
                top: 60px;
                right: 10px;
                background-color: rgba(0,0,0,0.7);
                color: white;
                padding: 15px;
                border-radius: 5px;
                z-index: 100;
                max-width: 300px;
                display: none;
            }}
            .progress-bar {{ width: 100%; background-color: #ddd; border-radius: 4px; margin: 5px 0; }}
            .progress-fill {{ height: 20px; border-radius: 4px; }}
            .cpu-fill {{ background-color: #f44336; }}
            .ram-fill {{ background-color: #2196F3; }}
            .disk-fill {{ background-color: #4CAF50; }}
        </style>
    </head>
    <body>
        <div id="info">
            {title} | <a href="/{'control' if not show_controls else ''}" style="color: white;">
                Switch to {'Control Panel' if not show_controls else 'Replica View'}
            </a>
        </div>
        
        <div id="stats">
            Active: <span id="active-count">0</span> | 
            In Use: <span id="user-count">0</span> | 
            Hardware Conflicts: <span id="hardware-conflict-count">0</span> |
            Software Conflicts: <span id="software-conflict-count">0</span> |
            Remote Sessions: <span id="remote-count">0</span>
        </div>
        
        <div id="pc-details">
            <h3 id="pc-title">PC Details</h3>
            <div id="pc-status"></div>
            <div id="pc-conflict-type"></div>
            <div id="pc-remote-status"></div>
            <div id="pc-location"></div>
            <div id="pc-last-updated"></div>
            <div id="pc-os-version"></div>
            <div id="pc-uptime"></div>
            
            <div>CPU: <span id="pc-cpu">0</span>%</div>
            <div class="progress-bar"><div id="cpu-bar" class="progress-fill cpu-fill" style="width: 0%"></div></div>
            
            <div>RAM: <span id="pc-ram">0</span>%</div>
            <div class="progress-bar"><div id="ram-bar" class="progress-fill ram-fill" style="width: 0%"></div></div>
            
            <div>Disk: <span id="pc-disk">0</span>%</div>
            <div class="progress-bar"><div id="disk-bar" class="progress-fill disk-fill" style="width: 0%"></div></div>
            
            <div id="pc-actions" style="margin-top: 10px;"></div>
            <button onclick="closeDetails()" style="margin-top: 10px; width: 100%;">Close</button>
        </div>
        
        <div id="controls">
            <button onclick="refreshData()">Refresh Data</button>
            <button onclick="resetCamera()">Reset View</button>
            <button onclick="toggleGrid()">Toggle Grid</button>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/controls/OrbitControls.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        
        <script>
            // Scene setup
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0xADD8E6);
            
            const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(10, 15, 15);
            
            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            document.body.appendChild(renderer.domElement);
            
            // Controls
            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.target.set(0, 0.5, 0);
            
            // Lighting
            const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
            scene.add(ambientLight);
            
            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(10, 20, 10);
            directionalLight.castShadow = true;
            directionalLight.shadow.mapSize.width = 2048;
            directionalLight.shadow.mapSize.height = 2048;
            scene.add(directionalLight);
            
            // Floor
            const floorWidth = 36;
            const floorDepth = 36;
            const floorGeometry = new THREE.PlaneGeometry(floorWidth, floorDepth);
            const floorMaterial = new THREE.MeshPhongMaterial({{ color: 0xAAAAAA }});
            const floor = new THREE.Mesh(floorGeometry, floorMaterial);
            floor.rotation.x = -Math.PI / 2;
            floor.receiveShadow = true;
            scene.add(floor);
            
            // Grid helper
            const gridHelper = new THREE.GridHelper(floorWidth, 36, 0xCCCCCC, 0x999999);
            gridHelper.position.y = 0.01;
            scene.add(gridHelper);
            
            // Walls
            const wallHeight = 8;
            const wallMaterial = new THREE.MeshPhongMaterial({{ color: 0xF0F0F0 }});
            const wallThickness = 0.2;
            
            // Front wall
            const frontWallGeometry = new THREE.BoxGeometry(floorWidth, wallHeight, wallThickness);
            const frontWall = new THREE.Mesh(frontWallGeometry, wallMaterial);
            frontWall.position.set(0, wallHeight / 2, -floorDepth / 2 - wallThickness / 2);
            frontWall.receiveShadow = true;
            scene.add(frontWall);
            
            // Back wall with door
            const doorWidth = 3;
            const doorHeight = 4;
            const wallSegmentWidth = (floorWidth - doorWidth) / 2;
            
            const backWallLeftGeometry = new THREE.BoxGeometry(wallSegmentWidth, wallHeight, wallThickness);
            const backWallLeft = new THREE.Mesh(backWallLeftGeometry, wallMaterial);
            backWallLeft.position.set(-wallSegmentWidth / 2 - doorWidth / 2, wallHeight / 2, floorDepth / 2 + wallThickness / 2);
            backWallLeft.receiveShadow = true;
            scene.add(backWallLeft);
            
            const backWallRightGeometry = new THREE.BoxGeometry(wallSegmentWidth, wallHeight, wallThickness);
            const backWallRight = new THREE.Mesh(backWallRightGeometry, wallMaterial);
            backWallRight.position.set(wallSegmentWidth / 2 + doorWidth / 2, wallHeight / 2, floorDepth / 2 + wallThickness / 2);
            backWallRight.receiveShadow = true;
            scene.add(backWallRight);
            
            // Door
            const doorGroup = new THREE.Group();
            doorGroup.position.set(-doorWidth / 2, 0, floorDepth / 2 + wallThickness / 2);
            doorGroup.rotation.y = -Math.PI / 4;
            
            const doorGeometry = new THREE.BoxGeometry(doorWidth, doorHeight, wallThickness * 1.1);
            const doorMaterial = new THREE.MeshPhongMaterial({{ color: 0x964B00 }});
            const door = new THREE.Mesh(doorGeometry, doorMaterial);
            door.position.set(doorWidth / 2, doorHeight / 2, 0);
            door.receiveShadow = true;
            doorGroup.add(door);
            scene.add(doorGroup);
            
            // Left wall
            const leftWallGeometry = new THREE.BoxGeometry(wallThickness, wallHeight, floorDepth + 2 * wallThickness);
            const leftWall = new THREE.Mesh(leftWallGeometry, wallMaterial);
            leftWall.position.set(-floorWidth / 2 - wallThickness / 2, wallHeight / 2, 0);
            leftWall.receiveShadow = true;
            scene.add(leftWall);
            
            // Right wall
            const rightWallGeometry = new THREE.BoxGeometry(wallThickness, wallHeight, floorDepth + 2 * wallThickness);
            const rightWall = new THREE.Mesh(rightWallGeometry, wallMaterial);
            rightWall.position.set(floorWidth / 2 + wallThickness / 2, wallHeight / 2, 0);
            rightWall.receiveShadow = true;
            scene.add(rightWall);
            
            // Ceiling
            const ceilingGeometry = new THREE.PlaneGeometry(floorWidth, floorDepth);
            const ceilingMaterial = new THREE.MeshPhongMaterial({{ color: 0xE0E0E0, side: THREE.DoubleSide }});
            const ceiling = new THREE.Mesh(ceilingGeometry, ceilingMaterial);
            ceiling.rotation.x = Math.PI / 2;
            ceiling.position.y = wallHeight;
            ceiling.receiveShadow = true;
            scene.add(ceiling);
            
            // Projector Screen
            const screenWidth = 8;
            const screenHeight = 4.5;
            const screenGeometry = new THREE.PlaneGeometry(screenWidth, screenHeight);
            const screenMaterial = new THREE.MeshBasicMaterial({{ color: 0xFFFFFF, side: THREE.DoubleSide }});
            const projectorScreen = new THREE.Mesh(screenGeometry, screenMaterial);
            const screenY = wallHeight * 0.6;
            projectorScreen.position.set(0, screenY, -floorDepth / 2 + wallThickness * 0.51);
            scene.add(projectorScreen);
            
            // Projector
            const projectorHeight = 0.3;
            const projectorStandHeight = screenY - (projectorHeight / 2) - 0.15;
            const projectorStandGeometry = new THREE.BoxGeometry(0.5, projectorStandHeight, 0.5);
            const projectorStandMaterial = new THREE.MeshPhongMaterial({{ color: 0x888888 }});
            const projectorStand = new THREE.Mesh(projectorStandGeometry, projectorStandMaterial);
            projectorStand.position.set(0, projectorStandHeight / 2, 9);
            projectorStand.castShadow = true;
            scene.add(projectorStand);
            
            const projectorGeometry = new THREE.BoxGeometry(1.0, projectorHeight, 1.2);
            const projectorMaterial = new THREE.MeshPhongMaterial({{ color: 0x333333 }});
            const projector = new THREE.Mesh(projectorGeometry, projectorMaterial);
            projector.position.set(0, projectorStandHeight + projectorHeight / 2, 9);
            projector.castShadow = true;
            scene.add(projector);
            
            // PC materials
            const pcMaterials = {{
                'active': new THREE.MeshPhongMaterial({{ color: 0x4CAF50, specular: 0x555555, shininess: 30 }}),
                'user': new THREE.MeshPhongMaterial({{ color: 0x2196F3, specular: 0x555555, shininess: 30 }}),
                'conflict': new THREE.MeshPhongMaterial({{ color: 0xf44336, specular: 0x555555, shininess: 30 }}),
                'backup': new THREE.MeshPhongMaterial({{ color: 0xFFC107, specular: 0x555555, shininess: 30 }})
            }};
            
            // PC models
            const pcMeshes = {{}};
            let pcs = [];
            let selectedPc = null;
            
            // Socket.io connection
            const socket = io();
            
            // Create a realistic PC model
            function createPCModel(pc) {{
                const group = new THREE.Group();
                
                // Desk
                const deskGeometry = new THREE.BoxGeometry(2.0 * pc.size_variation, 0.7, 1.5);
                const deskMaterial = new THREE.MeshPhongMaterial({{ color: 0x8B4513, specular: 0x555555, shininess: 10 }});
                const desk = new THREE.Mesh(deskGeometry, deskMaterial);
                desk.position.y = 0.35;
                desk.castShadow = true;
                desk.receiveShadow = true;
                group.add(desk);
                
                // PC Tower with LED
                const towerGeometry = new THREE.BoxGeometry(0.3 * pc.size_variation, 0.8, 0.8);
                const tower = new THREE.Mesh(towerGeometry, pcMaterials[pc.status]);
                tower.position.set(-0.8 * pc.size_variation, 0.4, 0);
                tower.castShadow = true;
                tower.receiveShadow = true;
                group.add(tower);
                
                // LED effect on tower
                const ledGeometry = new THREE.SphereGeometry(0.05 * pc.size_variation, 16, 16);
                const ledMaterial = new THREE.MeshBasicMaterial({{ color: pc.status === 'conflict' ? 0xff0000 : pc.remote_active ? 0xFFA500 : 0x00ff00 }});
                const led = new THREE.Mesh(ledGeometry, ledMaterial);
                led.position.set(-0.8 * pc.size_variation, 0.6, 0.41);
                group.add(led);
                
                // Monitor with stand
                const monitorGeometry = new THREE.BoxGeometry(1.2 * pc.size_variation, 0.7, 0.1);
                const monitor = new THREE.Mesh(monitorGeometry, new THREE.MeshPhongMaterial({{ color: 0x333333, specular: 0x555555, shininess: 50 }}));
                monitor.position.set(0, 0.85, -0.5);
                monitor.castShadow = true;
                monitor.receiveShadow = true;
                group.add(monitor);
                
                // Monitor stand
                const standGeometry = new THREE.BoxGeometry(0.4 * pc.size_variation, 0.2, 0.4);
                const stand = new THREE.Mesh(standGeometry, new THREE.MeshPhongMaterial({{ color: 0x333333 }}));
                stand.position.set(0, 0.45, -0.5);
                stand.castShadow = true;
                group.add(stand);
                
                // Screen
                const screenGeometry = new THREE.PlaneGeometry(1.0 * pc.size_variation, 0.6);
                const screenMaterial = new THREE.MeshBasicMaterial({{ 
                    color: pc.status === 'conflict' ? 0xff0000 : pc.remote_active ? 0xFFA500 : 0x000000,
                    side: THREE.DoubleSide
                }});
                const screen = new THREE.Mesh(screenGeometry, screenMaterial);
                screen.position.set(0, 0.85, -0.55);
                group.add(screen);
                
                // Keyboard
                const keyboardGeometry = new THREE.BoxGeometry(1.0 * pc.size_variation, 0.05, 0.4);
                const keyboard = new THREE.Mesh(keyboardGeometry, new THREE.MeshPhongMaterial({{ color: 0x222222 }}));
                keyboard.position.set(0, 0.375, -0.2);
                keyboard.castShadow = true;
                group.add(keyboard);
                
                // Position and rotation
                group.position.set(pc.x, 0, pc.z);
                group.rotation.y = pc.rotation_y;
                group.userData.pcId = pc.id;
                
                return group;
            }}
            
            // Load initial data
            function loadInitialData() {{
                fetch('/api/pcs')
                    .then(response => response.json())
                    .then(data => {{
                        pcs = data;
                        renderPCs();
                        updateStats();
                    }});
            }}
            
            // Render all PCs
            function renderPCs() {{
                Object.values(pcMeshes).forEach(mesh => scene.remove(mesh));
                Object.keys(pcMeshes).forEach(key => delete pcMeshes[key]);
                
                pcs.forEach(pc => {{
                    pcMeshes[pc.id] = createPCModel(pc);
                    scene.add(pcMeshes[pc.id]);
                }});
            }}
            
            // Update stats
            function updateStats() {{
                const active = pcs.filter(pc => pc.status === 'active').length;
                const user = pcs.filter(pc => pc.status === 'user').length;
                const hardwareConflict = pcs.filter(pc => pc.status === 'conflict' && pc.conflict_type === 'hardware_conflict').length;
                const softwareConflict = pcs.filter(pc => pc.status === 'conflict' && pc.conflict_type === 'software_conflict').length;
                const remoteSessions = pcs.filter(pc => pc.remote_active).length;
                
                document.getElementById('active-count').textContent = active;
                document.getElementById('user-count').textContent = user;
                document.getElementById('hardware-conflict-count').textContent = hardwareConflict;
                document.getElementById('software-conflict-count').textContent = softwareConflict;
                document.getElementById('remote-count').textContent = remoteSessions;
            }}
            
            // Show PC details
            function showPCDetails(pcId) {{
                const pc = pcs.find(p => p.id === pcId);
                if (!pc) return;
                
                selectedPc = pc;
                const details = document.getElementById('pc-details');
                
                document.getElementById('pc-title').textContent = pc.id;
                document.getElementById('pc-status').textContent = `Status: ${{pc.status.toUpperCase()}}`;
                document.getElementById('pc-conflict-type').textContent = pc.conflict_type ? `Conflict Type: ${{pc.conflict_type.replace('_', ' ').toUpperCase()}}` : '';
                document.getElementById('pc-remote-status').textContent = `Remote: ${{pc.remote_active ? 'Active' : 'Inactive'}}`;
                document.getElementById('pc-location').textContent = `Location: ${{pc.location}}`;
                document.getElementById('pc-last-updated').textContent = `Updated: ${{pc.last_updated}}`;
                document.getElementById('pc-os-version').textContent = `OS: ${{pc.os_version}}`;
                document.getElementById('pc-uptime').textContent = `Uptime: ${{pc.uptime}} hours`;
                
                document.getElementById('pc-cpu').textContent = pc.cpu;
                document.getElementById('cpu-bar').style.width = `${{pc.cpu}}%`;
                document.getElementById('pc-ram').textContent = pc.ram;
                document.getElementById('ram-bar').style.width = `${{pc.ram}}%`;
                document.getElementById('pc-disk').textContent = pc.disk;
                document.getElementById('disk-bar').style.width = `${{pc.disk}}%`;
                
                // Action buttons (only in control panel)
                const actionsDiv = document.getElementById('pc-actions');
                actionsDiv.innerHTML = '';
                
                if ({'true' if show_controls else 'false'}) {{
                    const actions = [
                        {{ name: 'Restart', action: 'restart', color: '#4CAF50' }},
                        {{ name: 'Shutdown', action: 'shutdown', color: '#f44336' }},
                        {{ name: 'Remote', action: 'remote', color: '#2196F3' }}
                    ];
                    
                    if (pc.status === 'conflict') {{
                        actions.push({{ name: 'Resolve', action: 'resolve', color: '#FFC107' }});
                    }}
                    if (pc.status === 'active') {{
                        actions.push({{ name: 'Assign', action: 'assign', color: '#2196F3' }});
                    }}
                    if (pc.status === 'user') {{
                        actions.push({{ name: 'Release', action: 'release', color: '#4CAF50' }});
                    }}
                    
                    actions.forEach(action => {{
                        const btn = document.createElement('button');
                        btn.textContent = action.name;
                        btn.style.backgroundColor = action.color;
                        btn.style.margin = '5px';
                        btn.onclick = () => handleAction(pc.id, action.action);
                        actionsDiv.appendChild(btn);
                    }});
                }}
                
                details.style.display = 'block';
            }}
            
            // Handle PC actions
            function handleAction(pcId, action) {{
                fetch(`/api/pcs/${{pcId}}/action`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ action: action }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        alert(data.message);
                    }} else {{
                        alert('Error: ' + data.message);
                    }}
                }});
            }}
            
            // Close details
            function closeDetails() {{
                document.getElementById('pc-details').style.display = 'none';
                selectedPc = null;
            }}
            
            // Refresh data
            function refreshData() {{
                fetch('/api/pcs/refresh', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            loadInitialData();
                        }}
                    }});
            }}
            
            // Reset camera
            function resetCamera() {{
                camera.position.set(10, 15, 15);
                controls.target.set(0, 0, 0);
                controls.update();
            }}
            
            // Toggle grid
            function toggleGrid() {{
                gridHelper.visible = !gridHelper.visible;
            }}
            
            // Handle clicks
            function onMouseClick(event) {{
                const mouse = new THREE.Vector2(
                    (event.clientX / window.innerWidth) * 2 - 1,
                    -(event.clientY / window.innerHeight) * 2 + 1
                );
                
                const raycaster = new THREE.Raycaster();
                raycaster.setFromCamera(mouse, camera);
                
                const intersects = raycaster.intersectObjects(Object.values(pcMeshes), true);
                
                if (intersects.length > 0) {{
                    let obj = intersects[0].object;
                    while (obj.parent && !obj.userData.pcId) {{
                        obj = obj.parent;
                    }}
                    if (obj.userData.pcId) {{
                        showPCDetails(obj.userData.pcId);
                    }}
                }}
            }}
            
            // Handle window resize
            function onWindowResize() {{
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            }}
            
            // Socket.io events
            socket.on('pc_update', (data) => {{
                const index = pcs.findIndex(p => p.id === data.pc.id);
                if (index !== -1) {{
                    pcs[index] = data.pc;
                    
                    // Update 3D model
                    if (pcMeshes[data.pc.id]) {{
                        scene.remove(pcMeshes[data.pc.id]);
                        pcMeshes[data.pc.id] = createPCModel(data.pc);
                        scene.add(pcMeshes[data.pc.id]);
                    }}
                    
                    updateStats();
                    
                    // Update details if open
                    if (selectedPc && selectedPc.id === data.pc.id) {{
                        showPCDetails(data.pc.id);
                    }}
                }}
            }});
            
            socket.on('pcs_refresh', (data) => {{
                pcs = data.pcs;
                renderPCs();
                updateStats();
            }});
            
            // Animation loop
            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                
                // Animate conflict PCs and remote sessions
                Object.values(pcMeshes).forEach(pcMesh => {{
                    const pc = pcs.find(p => p.id === pcMesh.userData.pcId);
                    if (pc) {{
                        const screen = pcMesh.children.find(
                            child => child.type === 'Mesh' && child.geometry.type === 'PlaneGeometry'
                        );
                        const led = pcMesh.children.find(
                            child => child.type === 'Mesh' && child.geometry.type === 'SphereGeometry'
                        );
                        if (screen && led) {{
                            if (pc.status === 'conflict') {{
                                const intensity = 0.5 + 0.5 * Math.sin(Date.now() * 0.005);
                                screen.material.color.setRGB(intensity, 0, 0);
                                led.material.color.setRGB(intensity, 0, 0);
                            }} else if (pc.remote_active) {{
                                const intensity = 0.5 + 0.5 * Math.sin(Date.now() * 0.003);
                                screen.material.color.setRGB(intensity, 0.5, 0);
                                led.material.color.setRGB(intensity, 0.5, 0);
                            }}
                        }}
                    }}
                }});
                
                renderer.render(scene, camera);
            }}
            
            // Event listeners
            window.addEventListener('click', onMouseClick, false);
            window.addEventListener('resize', onWindowResize, false);
            
            // Initialize
            loadInitialData();
            animate();
        </script>
    </body>
    </html>
    """

@app.route('/api/pcs', methods=['GET'])
def get_pcs():
    return jsonify(pcs_data)

@app.route('/api/pcs/refresh', methods=['POST'])
def refresh_pcs():
    try:
        for pc in pcs_data:
            if pc['status'] != 'backup':
                pc['cpu'] = random.randint(20, 80)
                pc['ram'] = random.randint(20, 90)
                pc['disk'] = random.randint(15, 55)
                pc['uptime'] = random.randint(1, 72)
            pc['last_updated'] = datetime.now().strftime('%H:%M:%S')
        emit_pc_update()
        return jsonify({'success': True, 'message': 'PC data refreshed', 'pcs': pcs_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/pcs/<pc_id>/action', methods=['POST'])
def pc_action(pc_id):
    data = request.get_json()
    action = data.get('action')

    pc = next((p for p in pcs_data if p['id'] == pc_id), None)
    if not pc:
        return jsonify({'success': False, 'message': 'PC not found'}), 404

    try:
        if action == 'restart':
            pc.update({
                'status': 'active',
                'cpu': random.randint(10, 40),
                'ram': random.randint(20, 60),
                'disk': random.randint(10, 30),
                'conflict_type': None,
                'uptime': 0
            })
            message = f'{pc_id} restarted successfully'
            
        elif action == 'shutdown':
            pc.update({
                'cpu': 0,
                'ram': 0,
                'disk': 0,
                'status': 'active' if pc['status'] in ['user', 'conflict'] else pc['status'],
                'remote_active': False,
                'uptime': 0
            })
            message = f'{pc_id} shutdown complete'
            
        elif action == 'remote':
            pc['remote_active'] = not pc['remote_active']
            message = f'{pc_id} remote session {"started" if pc["remote_active"] else "ended"}'
            
        elif action == 'resolve' and pc['status'] == 'conflict':
            pc.update({
                'status': 'active',
                'cpu': random.randint(10, 40),
                'ram': random.randint(20, 60),
                'disk': random.randint(10, 30),
                'conflict_type': None
            })
            message = f'{pc_id} conflict resolved'
            
        elif action == 'assign' and pc['status'] == 'active':
            pc.update({
                'status': 'user',
                'cpu': random.randint(40, 80),
                'ram': random.randint(50, 90),
                'disk': random.randint(20, 50)
            })
            message = f'{pc_id} assigned to user'
            
        elif action == 'release' and pc['status'] == 'user':
            pc.update({
                'status': 'active',
                'cpu': random.randint(10, 40),
                'ram': random.randint(20, 60),
                'disk': random.randint(10, 30),
                'remote_active': False
            })
            message = f'{pc_id} released from user'
            
        else:
            return jsonify({'success': False, 'message': 'Invalid action or status'}), 400

        pc['last_updated'] = datetime.now().strftime('%H:%M:%S')
        emit_pc_update(pc_id)
        return jsonify({'success': True, 'message': message, 'pc': pc})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

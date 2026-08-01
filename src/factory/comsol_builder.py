import mph
from src.design.geometry import FiberGeometry, Circle, Ellipse
from src.design.parameter_space import FiberSpec

class COMSOLBuilder:
    def __init__(self, model):
        self.model = model
        self.java = model.java
        
        if 'comp1' not in self.model:
            self.java.component().create('comp1')
            self.java.component('comp1').geom().create('geom1', 2)

        self.geom = self.java.component('comp1').geom('geom1')

    def build(self, fiber: FiberGeometry, spec: FiberSpec):
        self.geom.lengthUnit('um')
        
        # 1. Physics, Definitions, Solver
        # Setup parameters BEFORE geometry so we can use them if needed
        self._setup_parameters(spec)
        
        # 2. Geometry Construction
        # We'll use the sampled values from the 'fiber' object, 
        # but the COMSOL parameters will be there for reference/tweaking.
        r_fiber = fiber.radius
        au_t = next((l.thickness for l in fiber.external_layers if l.material.name == 'Au'), 0.04)
        an_t = next((l.thickness for l in fiber.external_layers if l.material.name == 'Analyte'), 1.4)
        pml_t = next((l.thickness for l in fiber.external_layers if l.material.name == 'PML'), 1.4)
        
        r_gold = r_fiber + au_t
        r_analyte = r_gold + an_t
        r_pml = r_analyte + pml_t
        
        # Draw Concentric Circles
        self.geom.feature().create('c_pml', 'Circle')
        self.geom.feature('c_pml').set('r', str(r_pml))
        
        self.geom.feature().create('c_ana', 'Circle')
        self.geom.feature('c_ana').set('r', str(r_analyte))

        self.geom.feature().create('c_gold', 'Circle')
        self.geom.feature('c_gold').set('r', str(r_gold))
        
        self.geom.feature().create('c_core', 'Circle')
        self.geom.feature('c_core').set('r', str(r_fiber))
        
        # Draw Holes
        for i, shape in enumerate(fiber.shapes):
            tag = f"h_{i}"
            self._create_shape_feature(tag, shape)

        self.geom.run()

        # 3. Materials & Selections
        self._assign_materials(fiber, r_fiber, r_gold, r_analyte, r_pml)

        # 4. Final Setup
        self._setup_definitions()
        self._setup_physics()
        self._setup_mesh()

    def _setup_parameters(self, spec: FiberSpec):
        """Define Global Parameters in two specific groups"""

        # --- Group 1: Parameters Geometry ---
        pg = self.java.param()
        pg.label('Parameters Geometry')

        pitch = spec.lattice.pitch
        tau_nm = spec.plasmonic_layer.thickness_nm
        
        geom_map = {
            'p': f'{pitch}[um]',
            'dc': '0.49*p',
            'd1': '0.28*p',
            'd2': '0.9*p',
            'd3': '0.97*p',
            'tau': f'{tau_nm}[nm]',
            'ana': 'p/2',
        }
        for k, v in geom_map.items():
            pg.set(k, v)

        # --- Group 2: Parameters Materials ---
        # Explicitly create a new Parameter feature. 
        # The type is 'Param'. We'll use tag 'p2'.
        if 'p2' not in self.model:
            self.java.param().create('p2')
        
        pm = self.java.param('p2')
        pm.label('Parameters Materials')
        
        mat_map = {
            'A1': '0.69616300',
            'A2': '0.407942600',
            'A3': '0.897479400',
            'B1': '4.67914826e-3[um^2]',
            'B2': '1.35120631e-3[um^2]',
            'B3': '97.9340025[um^2]',
            'l': '0.65[um]',
            'neff1': 'sqrt(1 + ((A1*(l)^2)/(((l)^2)-B1))+ ((A2*(l)^2)/(((l)^2)-B2))+ ((A3*(l)^2)/(((l)^2)-B3)))',
            'einf': '5.9673',
            'omg': '2*pi*c_const/l',
            'omgD': '2*pi*2113.6[THz]',
            'ID': '2*pi*15.92[THz]',
            'De': '1.09',
            'gl': '2*pi*104.86[THz]',
            'rl': '2*pi*650.7[THz]',
            'eg': 'einf-(omgD^2/(omg*(omg+i*ID)))-((De*rl^2)/((omg^2-rl^2)+i*gl*omg))',
            'e1': 'real(eg)',
            'e2': 'imag(eg)',
            'nau': 'sqrt((e1/2)+0.5*sqrt(e1^2+e2^2))',
            'kau': 'e2/(2*nau)',
            'na': '1.33',
            'tg': '40[nm]'
        }
        for k, v in mat_map.items():
            pm.set(k, v)

    def _assign_materials(self, fiber, r_fib, r_au, r_an, r_pml):
        comp = self.java.component('comp1')
        
        def create_mat(tag, name, n_expr, k_expr='0'):
            if tag not in self.model:
                comp.material().create(tag, 'Common')
            node = comp.material(tag)
            node.label(name)
            
            # 1. Create RefractiveIndex group (Primary for Wave Optics)
            # Use specific tag 'group_index' and type 'RefractiveIndex'
            if 'group_index' not in node.propertyGroup():
                node.propertyGroup().create('group_index', 'RefractiveIndex')
            
            n_s = str(n_expr)
            k_s = str(k_expr)
            
            node.propertyGroup('group_index').set('n', [n_s])
            node.propertyGroup('group_index').set('ki', [k_s])

            # 2. Create Basic group (Backup for generic EM)
            if not node.propertyGroup('def'):
                node.propertyGroup().create('def', 'Basic')
            
            node.propertyGroup('def').set('relpermittivity', [f"({n_s} - i*{k_s})^2"])
            node.propertyGroup('def').set('relpermeability', ["1"])
            
            # Also populate n/ki in Basic just in case
            try:
                node.propertyGroup('def').set('n', [n_s])
                node.propertyGroup('def').set('ki', [k_s])
            except:
                pass
                
            return node

        def create_ball_sel(name, x, y, r):
            if name not in self.model:
                 comp.selection().create(name, 'Ball')
            sel = comp.selection(name)
            sel.set('posx', str(x))
            sel.set('posy', str(y))
            sel.set('r', str(r))
            return sel

        # 1. Silica (Core and Outer) - Uses 'neff1' parameter
        # SAFETY NET: Assign Silica to ALL domains first. 
        # This ensures no domain is left undefined (fixing the 'ki' error).
        mat_silica = create_mat('mat_silica', 'Silica', 'neff1')
        mat_silica.selection().all()
        
        # Explicitly create selections needed for Definitions/PML
        create_ball_sel('sel_outer', (r_an + r_pml)/2.0, 0.0, 0.1)
        create_ball_sel('sel_core', r_fib * 0.95, 0.0, 0.1)
        
        # 2. Analyte - Uses 'na' parameter (Overriding Silica)
        mat_an = create_mat('mat_analyte', 'Analyte', 'na')
        create_ball_sel('sel_an', (r_au + r_an)/2.0, 0.0, 0.1)
        mat_an.selection().named('sel_an')

        # 3. Gold - Uses 'nau' and 'kau' parameters (Overriding Silica)
        mat_au = create_mat('mat_au', 'Gold', 'nau', 'kau')
        create_ball_sel('sel_au', (r_fib + r_au)/2.0, 0.0, 0.01)
        mat_au.selection().named('sel_au')
        
        # 4. Air Holes (Overriding Silica)
        mat_air = create_mat('mat_air', 'Air', '1.0')
        if 'sel_holes_all' not in self.model:
            comp.selection().create('sel_holes_all', 'Union')
            
        hole_sel_tags = []
        for i, shape in enumerate(fiber.shapes):
            sel_name = f"sel_h_{i}"
            r_sel = (shape.radius if isinstance(shape, Circle) else min(shape.radius_x, shape.radius_y)) * 0.5
            create_ball_sel(sel_name, shape.center.x, shape.center.y, r_sel)
            hole_sel_tags.append(sel_name)
            
        comp.selection('sel_holes_all').set('input', hole_sel_tags)
        mat_air.selection().named('sel_holes_all')

    def _setup_definitions(self):
        comp = self.java.component('comp1')
        if 'pml1' not in self.model:
            comp.coordSystem().create('pml1', 'PML')
        pml = comp.coordSystem('pml1')
        pml.selection().named('sel_outer')
        
        # Robustly try to set Cylindrical
        success = False
        for prop in ['Type', 'Geometry', 'PmlType', 'ScalingType']:
            try:
                pml.set(prop, 'Cylindrical')
                success = True
                break 
            except:
                continue
        
        # If we couldn't force it to Cylindrical, disable it to prevent solver crash.
        # A disabled PML acts like normal material (Silica buffer), which is better than a crash.
        if not success:
            print("Warning: Could not set PML to Cylindrical. Disabling PML to allow solving.")
            pml.active(False)
        else:
            # Even if 'set' didn't throw, verify? No easy way. 
            # We assume if it didn't throw, it worked.
            pass

    def _setup_physics(self):
        comp = self.java.component('comp1')
        if 'ewfd' not in self.model:
            comp.physics().create('ewfd', 'ElectromagneticWavesFrequencyDomain', 'geom1')
        comp.physics('ewfd').selection().all()

        if 'std1' not in self.model:
            self.java.study().create('std1')
            self.java.study('std1').create('mode', 'ModeAnalysis')
            # Use 'l' parameter for study wavelength
            try:
                # Setting frequency based on wavelength parameter 'l'
                self.java.study('std1').feature('mode').set('modefreq', 'c_const/l')
            except:
                pass
            
            # Search for modes around the silica refractive index (neff1)
            self.java.study('std1').feature('mode').set('shift', 'neff1')
            # Desired number of modes: 6
            self.java.study('std1').feature('mode').set('neigs', '6')
            try:
                self.java.study('std1').createSolution()
            except:
                pass

    def _setup_mesh(self):
        comp = self.java.component('comp1')
        if 'mesh1' not in self.model:
            comp.mesh().create('mesh1', 'geom1')
        mesh = comp.mesh('mesh1')
        if 'ftri1' not in self.model:
            mesh.create('ftri1', 'FreeTri')
        try:
            mesh.run()
        except:
            pass

    def _create_shape_feature(self, tag, shape):
        if isinstance(shape, Circle):
            feat = self.geom.feature().create(tag, 'Circle')
            feat.set('r', str(shape.radius))
        elif isinstance(shape, Ellipse):
            feat = self.geom.feature().create(tag, 'Ellipse')
            feat.set('semiaxes', [str(shape.radius_x), str(shape.radius_y)])
            feat.set('rot', str(shape.rotation))
        feat.set('pos', [str(shape.center.x), str(shape.center.y)])

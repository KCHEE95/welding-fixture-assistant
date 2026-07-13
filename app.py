import streamlit as st
import trimesh
import numpy as np
import tempfile
import os
import plotly.graph_objects as go

# 页面配置
st.set_page_config(page_title="焊接工装设计副驾驶", layout="wide")
st.title("🔧 焊接工装设计副驾驶 (钣金简易版)")
st.markdown("上传你的钣金 STEP 模型，获取老师傅的工装设计思路")

# 上传组件
uploaded_file = st.file_uploader(
    "上传 3D 模型 (支持 STL / STEP 格式)", 
    type=["stl", "stp", "step"]
)

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    with st.spinner("正在加载模型，请稍候..."):
        try:
            # --- 处理 STEP 格式 ---
            if file_extension in ['stp', 'step']:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.stp') as tmp_input:
                    tmp_input.write(file_bytes)
                    tmp_input_path = tmp_input.name
                
                loaded = trimesh.load(tmp_input_path, file_type='stp')
                os.unlink(tmp_input_path)
                
                # 如果是 Scene，提取并合并所有几何体
                if isinstance(loaded, trimesh.Scene):
                    meshes = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
                    if not meshes:
                        raise ValueError("未找到任何有效的三角网格")
                    mesh = trimesh.util.concatenate(meshes)
                else:
                    mesh = loaded
                
                # 检查网格是否有效
                if mesh.vertices.shape[0] == 0:
                    raise ValueError("网格不包含任何顶点")
                
                # 获取顶点和三角面（用于 Plotly）
                vertices = mesh.vertices
                faces = mesh.faces
                bbox = mesh.bounding_box.extents
                face_count = len(faces)
                
            else:  # STL 格式
                mesh = trimesh.load(uploaded_file, file_type='stl')
                vertices = mesh.vertices
                faces = mesh.faces
                bbox = mesh.bounding_box.extents
                face_count = len(faces)
                
            is_valid = True
            
        except Exception as e:
            st.error(f"❌ 无法加载或解析文件，错误信息：{e}")
            st.info("💡 提示：请确认上传的是有效的 STEP (.stp) 或 STL (.stl) 文件。")
            st.stop()

    # --- 使用 Plotly 显示 3D 模型 ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📐 工件预览")
        # 创建 Mesh3d 对象
        fig = go.Figure(data=[
            go.Mesh3d(
                x=vertices[:,0],
                y=vertices[:,1],
                z=vertices[:,2],
                i=faces[:,0],
                j=faces[:,1],
                k=faces[:,2],
                color='#FF9900',
                opacity=0.8,
                flatshading=True
            )
        ])
        # 设置相机视角，让模型居中
        fig.update_layout(
            scene=dict(
                aspectmode='data',
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='Z'
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 模型信息")
        st.write(f"**尺寸 (长×宽×高)**: {bbox[0]:.1f} × {bbox[1]:.1f} × {bbox[2]:.1f} mm")
        st.write(f"**三角面片数**: {face_count:,}")
        st.write(f"**文件格式**: {file_extension.upper()}")

    # --- 用户选择产品类型 ---
    product_type = st.selectbox(
        "请选择您要焊接的产品类型（帮助提供针对性建议）",
        ["L型角钢带三角支撑", "平板拼接", "其他 / 自定义"]
    )

    if st.button("🧠 生成工装设计思路", type="primary"):
        st.subheader("📋 老师傅的设计建议")
        st.divider()

        base_x = bbox[0] + 120
        base_y = bbox[1] + 120
        clamp_count = 3 if bbox[0] > 300 else 2

        if product_type == "L型角钢带三角支撑":
            st.markdown(f"""
            **基于您选择的“L型角钢 + 三角板满焊”结构，量身定制建议如下：**

            **1. 摆放姿态**  
            将 L 型角钢的**底面**朝下平放于工装底板上，三角板保持**垂直向上**焊接。  
            （最大平面朝下，利于稳定）

            **2. 底板尺寸**  
            建议切割一块 **{base_x:.0f} × {base_y:.0f} × 10 mm** 的钢板作为底座（比工件长宽各大 60~100 mm）。

            **3. 定位方案**  
            - 使用两块 **L 型限位块**（折弯 90°，厚度 8 mm）卡住角钢的两个外直角边，限制 X/Y 方向移动。  
            - 在角钢两端各加一块 **端面挡块**（厚度 8 mm），防止轴向窜动。

            **4. 三角板支撑**  
            在三角板正下方的底板上，焊接一个 **支撑台**（高度需匹配三角板底边位置），托住三角板，保证垂直度。

            **5. 快速夹钳布局**  
            - 在角钢平面上方布置 **{clamp_count} 个垂直式快速夹钳**（如 GH-301），均匀分布，向下压紧。  
            - 在三角板顶部侧面安装 **1 个水平式推拉夹钳**，防止焊接时向后倾倒。  
            - 在三角板正面（焊缝对面）再加 **1 个推拉夹钳**，顶紧消除间隙。

            **6. 下料清单（供 SW48 切割）**  
            - 底板 × 1 (10mm 钢板)  
            - L 型限位块 × 2 (8mm 钢板，需折弯)  
            - 端面挡块 × 2 (8mm 钢板)  
            - 三角支撑台 × 1 (10mm 钢板，高度按需)  
            - 夹钳安装座 × {clamp_count + 2} 块小钣金

            **7. 焊接特别叮嘱（非常重要）**  
            ⚠️ 满焊热量大，必须严格按顺序操作：  
            - 先点焊定位三角板，确认垂直度。  
            - 采用 **对称分段焊**：左边焊 50mm 立刻跳到右边焊 50mm，反复交替，**严禁**从一头连续焊到尾。  
            - 焊后 **保持夹紧状态自然冷却 5~10 分钟**，再松开工装，否则角钢会严重变形。
            """)

        elif product_type == "平板拼接":
            st.markdown(f"""
            **基于“平板拼接”件的工装建议：**

            - 以**最大平面**为基准，平放在底板上。  
            - 底板建议尺寸：{base_x:.0f} × {base_y:.0f} × 10 mm。  
            - 周边布置限位块，并采用 **{clamp_count} 个快速夹钳** 压紧。  
            - 注意夹钳位置要避开焊缝路径，保证焊枪操作空间。  
            - 若拼接板较薄，可增加支撑点防止下塌。
            """)

        else:
            st.markdown(f"""
            **通用工装设计原则（适用于大多数钣金焊接件）：**

            1. **定位基准**：优先选择工件上最大的平面或精度要求最高的面作为基准。  
            2. **3-2-1 定位规则**：限制 6 个自由度（3 个支撑点确定基准面，2 个点限制平移，1 个点限制旋转）。  
            3. **夹紧力**：作用点应靠近定位支撑面，且不引起工件变形。  
            4. **标准件优先**：尽量使用标准快速夹钳（如 GH 系列），降低制造成本。  
            5. **空间预留**：工装设计要便于装卸工件，且不妨碍焊枪移动。  
            6. **底板推荐尺寸**：{base_x:.0f} × {base_y:.0f} × 10 mm，根据实际工件调整。
            """)

        st.success("💡 拿到以上建议后，你可以在 SolidWorks 中快速绘制各钣金件，导出 DXF 用 SW48 切割，然后点焊组装成简易工装。")
        st.info("📌 提示：本工具为设计辅助，最终工装需结合实际工艺微调。")

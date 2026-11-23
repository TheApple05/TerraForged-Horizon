//! TerraForged controls for the game's world-preset editor.
use std::sync::Mutex;

use mod_api::client::widgets::{Button, Outcome, WidgetId, Widgets};
use mod_api::serde_json::{Map, Value};
use mod_api::{
    ClientHost, Compound, DrawContext, Flow, PresetEditor, RegisterPresetEditorsEvent,
    ScreenClosingEvent, ScreenKeyPressedPreEvent, ScreenMouseButtonPressedPreEvent,
    ScreenMouseButtonReleasedPreEvent, ScreenMouseDraggedPreEvent, ScreenRenderPostEvent, Tag,
    Text,
};

use super::{PRESET, preset_editor};
use preset_editor::{FIELDS, Field, Kind, apply_overrides};

const PRESET_ID: &str = "terraforged:default";
const EDITOR_ID: &str = "terraforged:customize";
const SCREEN_ID: &str = "world_preset_editor";
const CLASSIC: &str = "/miscellaneous/classicBiomeVariants";
const MOBILE_HEIGHT: f32 = 106.0;

pub(super) fn register(event: &mut RegisterPresetEditorsEvent<'_>) {
    event.editors.push(PresetEditor {
        preset: PRESET_ID.into(),
        screen: EDITOR_ID.into(),
    });
}

fn is_editor(host: &dyn ClientHost) -> bool {
    host.preset_editor()
        .is_some_and(|editor| editor.preset == PRESET_ID && editor.screen == EDITOR_ID)
}

#[derive(Default)]
pub(super) struct Customize(Mutex<Option<Result<Menu, ()>>>);

impl Customize {
    pub(super) fn render(&self, host: &dyn ClientHost, event: &mut ScreenRenderPostEvent<'_>) {
        if !is_editor(host) {
            return;
        }
        let mut state = self.0.lock().expect("TerraForged preset editor lock");
        let Ok(menu) = state.get_or_insert_with(|| Menu::open(host).ok_or(())) else {
            centered(event.draw, host, "terraforged.customize.unavailable", 10.0);
            return;
        };
        menu.draw(host, event.draw, event.screen.mouse);
    }

    pub(super) fn close(&self, event: &ScreenClosingEvent<'_>) {
        if event.screen.id == SCREEN_ID {
            *self.0.lock().expect("TerraForged preset editor lock") = None;
        }
    }

    pub(super) fn mouse_pressed(
        &self,
        host: &dyn ClientHost,
        event: &ScreenMouseButtonPressedPreEvent<'_>,
    ) -> Flow {
        self.input(host, |menu| {
            let mouse = event.screen.mouse;
            let outcome = menu
                .widgets
                .mouse_pressed(host, mouse, event.button, event.modifiers);
            if let Outcome::Pressed(id) = outcome {
                menu.mouse_captured = true;
                menu.press(host, id, Some(mouse[0]));
            }
            outcome.handled()
        })
    }

    pub(super) fn mouse_released(
        &self,
        host: &dyn ClientHost,
        event: &ScreenMouseButtonReleasedPreEvent<'_>,
    ) -> Flow {
        self.input(host, |menu| {
            if event.button == 0 {
                menu.dragging = None;
                menu.widgets.mouse_released(event.button);
                return std::mem::take(&mut menu.mouse_captured);
            }
            false
        })
    }

    pub(super) fn mouse_dragged(
        &self,
        host: &dyn ClientHost,
        event: &ScreenMouseDraggedPreEvent<'_>,
    ) -> Flow {
        if event.button != 0 {
            return Flow::Continue;
        }
        self.input(host, |menu| {
            if let Some(index) = menu.dragging {
                menu.slide(host, index, event.screen.mouse[0]);
            }
            menu.mouse_captured
        })
    }

    pub(super) fn key_pressed(
        &self,
        host: &dyn ClientHost,
        event: &ScreenKeyPressedPreEvent<'_>,
    ) -> Flow {
        self.input(host, |menu| {
            menu.key_pressed(host, event.key, event.modifiers)
        })
    }

    fn input(&self, host: &dyn ClientHost, input: impl FnOnce(&mut Menu) -> bool) -> Flow {
        if !is_editor(host) {
            return Flow::Continue;
        }
        let mut state = self.0.lock().expect("TerraForged preset editor lock");
        if state
            .as_mut()
            .and_then(|menu| menu.as_mut().ok())
            .is_some_and(input)
        {
            Flow::Cancel
        } else {
            Flow::Continue
        }
    }
}

#[derive(Clone, Copy, PartialEq)]
struct Layout {
    x: f32,
    width: f32,
    rows: usize,
}

impl Layout {
    fn new([width, height]: [f32; 2]) -> Option<Self> {
        if width < 174.0 || height < MOBILE_HEIGHT {
            return None;
        }
        let panel = (width - 16.0).min(300.0);
        Some(Self {
            x: ((width - panel) / 2.0).floor(),
            width: panel,
            rows: (((height - 83.0) / 22.0).floor() as usize).clamp(1, FIELDS.len()),
        })
    }
}

struct Menu {
    defaults: Value,
    active: Value,
    classic: bool,
    widgets: Widgets,
    field_ids: Vec<(WidgetId, usize)>,
    navigation: Option<[WidgetId; 3]>,
    layout: Option<Layout>,
    page: usize,
    mouse_captured: bool,
    dragging: Option<usize>,
    error: bool,
}

impl Menu {
    fn open(host: &dyn ClientHost) -> Option<Self> {
        let defaults = mod_api::serde_json::from_str(PRESET).ok()?;
        let (overrides, classic) = read_overrides(&mut host.preset_editor_dimensions()?)?;
        let active = apply_overrides(&defaults, &overrides).ok()?;
        Some(Self {
            defaults,
            active,
            classic,
            widgets: Widgets::new(),
            field_ids: Vec::new(),
            navigation: None,
            layout: None,
            page: 0,
            mouse_captured: false,
            dragging: None,
            error: false,
        })
    }

    fn rebuild(&mut self) {
        self.widgets = Widgets::new();
        self.field_ids.clear();
        self.navigation = None;
        self.dragging = None;
        let Some(layout) = self.layout else {
            return;
        };
        let page_count = FIELDS.len().div_ceil(layout.rows);
        self.page = self.page.min(page_count - 1);
        let x = layout.x;
        let width = layout.width;
        let mut previous = Button::new([x, 25.0, 30.0, 20.0], tr("terraforged.customize.previous"));
        previous.active = self.page != 0;
        let mut next = Button::new(
            [x + 34.0, 25.0, 30.0, 20.0],
            tr("terraforged.customize.next"),
        );
        next.active = self.page + 1 < page_count;
        let reset = Button::new(
            [x + width - 55.0, 25.0, 55.0, 20.0],
            tr("terraforged.customize.reset"),
        );
        self.navigation = Some([
            self.widgets.add_button(previous),
            self.widgets.add_button(next),
            self.widgets.add_button(reset),
        ]);
        for (row, index) in (self.page * layout.rows..FIELDS.len())
            .take(layout.rows)
            .enumerate()
        {
            let field = FIELDS[index];
            let mut button = Button::new(
                [x, 49.0 + row as f32 * 22.0, width, 20.0],
                label(field, &self.active, self.classic),
            );
            button.active = self.classic || field.path != CLASSIC;
            self.field_ids
                .push((self.widgets.add_button(button), index));
        }
    }

    fn draw(&mut self, host: &dyn ClientHost, draw: &mut dyn DrawContext, mouse: [f32; 2]) {
        let layout = Layout::new(draw.size());
        if layout != self.layout {
            self.layout = layout;
            self.rebuild();
        }
        let Some(layout) = layout else {
            centered(draw, host, "terraforged.customize.resize", 10.0);
            return;
        };
        centered(
            draw,
            host,
            if self.error {
                "terraforged.customize.refused"
            } else {
                "terraforged.customize.title"
            },
            10.0,
        );
        let page_count = FIELDS.len().div_ceil(layout.rows);
        let page = format!("{} / {}", self.page + 1, page_count);
        let center = layout.x + (layout.width + 9.0) * 0.5;
        draw.text(
            &page,
            [center - draw.text_width(&page) * 0.5, 31.0],
            u32::MAX,
            true,
        );
        let _ = self.widgets.draw(draw, host, mouse);
        for &(id, index) in &self.field_ids {
            let field = FIELDS[index];
            if let Kind::Number { min, max, .. } = field.kind
                && let Some(button) = self.widgets.button(id)
                && let Some(value) = self.active.pointer(field.path).and_then(Value::as_f64)
            {
                let [x, y, width, _] = button.rect;
                let range = width - 14.0;
                let thumb_x = x + 7.0 + range * ((value - min) / (max - min)) as f32;
                draw.fill([x + 7.0, y + 16.0, range, 1.0], 0xFF34_3434);
                draw.fill([thumb_x - 2.0, y + 15.0, 4.0, 3.0], 0xFFF2_F2F2);
            }
        }
    }

    fn press(&mut self, host: &dyn ClientHost, id: WidgetId, x: Option<f32>) {
        if let Some([previous, next, reset]) = self.navigation {
            if id == previous || id == next {
                self.page = self
                    .page
                    .saturating_add_signed(if id == previous { -1 } else { 1 });
                self.rebuild();
                return;
            }
            if id == reset {
                self.save(host, Map::clear);
                return;
            }
        }
        let Some(index) = self.field_for(id) else {
            return;
        };
        match FIELDS[index].kind {
            Kind::Boolean => {
                let field = FIELDS[index];
                if let Some(value) = self.active.pointer(field.path).and_then(Value::as_bool) {
                    self.change(host, field, Value::Bool(!value));
                }
            }
            Kind::Number { .. } if let Some(x) = x => {
                self.dragging = Some(index);
                self.slide(host, index, x);
            }
            _ => {}
        }
    }

    fn field_for(&self, id: WidgetId) -> Option<usize> {
        self.field_ids
            .iter()
            .find_map(|&(field, index)| (field == id).then_some(index))
    }

    fn slide(&mut self, host: &dyn ClientHost, index: usize, x: f32) {
        let Some(layout) = self.layout else {
            return;
        };
        let field = FIELDS[index];
        if let Kind::Number {
            min,
            max,
            step,
            integer,
        } = field.kind
        {
            let position =
                f64::from(((x - layout.x - 7.0) / (layout.width - 14.0)).clamp(0.0, 1.0));
            let value = (position * (max - min) / step).round().mul_add(step, min);
            self.change(host, field, slider_value(value, min, max, integer));
        }
    }

    fn key_pressed(&mut self, host: &dyn ClientHost, key: &str, modifiers: u32) -> bool {
        if key == "key.keyboard.tab" && modifiers & 2 != 0 {
            self.widgets.set_focus(host, None);
            return false;
        }
        if matches!(key, "key.keyboard.left" | "key.keyboard.right")
            && let Some(&field) = self
                .widgets
                .focused()
                .and_then(|id| self.field_for(id))
                .and_then(|index| FIELDS.get(index))
            && let Kind::Number {
                min,
                max,
                step,
                integer,
            } = field.kind
            && let Some(value) = self.active.pointer(field.path).and_then(Value::as_f64)
        {
            let adjusted = if key == "key.keyboard.left" {
                value - step
            } else {
                value + step
            };
            self.change(host, field, slider_value(adjusted, min, max, integer));
            return true;
        }
        let outcome = self.widgets.key_pressed(host, key, modifiers);
        if let Outcome::Pressed(id) = outcome {
            self.press(host, id, None);
        }
        outcome.handled()
    }

    fn change(&mut self, host: &dyn ClientHost, field: Field, value: Value) {
        if self.active.pointer(field.path) == Some(&value) {
            return;
        }
        let default = self.defaults.pointer(field.path).is_some_and(|default| {
            default == &value
                || default
                    .as_f64()
                    .zip(value.as_f64())
                    .is_some_and(|(a, b)| a == b)
        });
        self.save(host, |overrides| {
            if default {
                overrides.remove(field.path);
            } else {
                overrides.insert(field.path.into(), value);
            }
        });
    }

    fn save(&mut self, host: &dyn ClientHost, edit: impl FnOnce(&mut Map<String, Value>)) {
        self.error = true;
        let Some(mut dimensions) = host.preset_editor_dimensions() else {
            return;
        };
        let Some((mut overrides, classic)) = read_overrides(&mut dimensions) else {
            return;
        };
        edit(&mut overrides);
        let Ok(active) = apply_overrides(&self.defaults, &overrides) else {
            return;
        };
        if !write_overrides(&mut dimensions, &overrides)
            || !host.set_preset_editor_dimensions(dimensions)
        {
            return;
        }
        self.error = false;
        self.active = active;
        self.classic = classic;
        for &(id, index) in &self.field_ids {
            if let Some(button) = self.widgets.button_mut(id) {
                button.label = label(FIELDS[index], &self.active, self.classic);
            }
        }
    }
}

fn tr(key: &str) -> Text {
    Text::translate(key, Vec::new())
}

fn centered(draw: &mut dyn DrawContext, host: &dyn ClientHost, key: &str, y: f32) {
    if let Some(title) = host.translate(key) {
        draw.text(
            &title,
            [(draw.size()[0] - draw.text_width(&title)) * 0.5, y],
            u32::MAX,
            true,
        );
    }
}

fn label(field: Field, active: &Value, classic: bool) -> Text {
    let value = if field.path == CLASSIC && !classic {
        tr("terraforged.customize.classic_unavailable")
    } else {
        match active.pointer(field.path) {
            Some(Value::Bool(true)) => tr("options.on"),
            Some(Value::Bool(false)) => tr("options.off"),
            Some(value) => Text::literal(value.to_string()),
            None => return tr(field.label),
        }
    };
    Text::translate("options.generic_value", vec![tr(field.label), value])
}

fn slider_value(value: f64, min: f64, max: f64, integer: bool) -> Value {
    let value = ((value * 100_000.0).round() / 100_000.0).clamp(min, max);
    if integer {
        Value::from(value.round() as i64)
    } else {
        Value::from(value)
    }
}

fn declared_type(node: &Compound, expected: &str) -> bool {
    matches!(node.get(&"type".into()), Some(Tag::String(name)) if *name == expected.into())
}

fn visit_cells(
    tag: &mut Tag,
    depth: u32,
    visit: &mut impl FnMut(&mut Compound) -> Option<()>,
) -> Option<()> {
    if depth == 128 {
        return None;
    }
    match tag {
        Tag::Compound(node) if declared_type(node, "terraforged:cell") => visit(node)?,
        Tag::Compound(node) => {
            for child in node.values_mut() {
                visit_cells(child, depth + 1, visit)?;
            }
        }
        Tag::List(children) => {
            for child in children {
                visit_cells(child, depth + 1, visit)?;
            }
        }
        _ => {}
    }
    Some(())
}

fn visit_targets(
    dimensions: &mut Compound,
    mut visit: impl FnMut(&mut Compound) -> Option<()>,
) -> Option<bool> {
    let Tag::Compound(generator) = dimensions
        .get_mut(&"minecraft:overworld".into())?
        .get_mut("generator")?
    else {
        return None;
    };
    let settings = generator.get_mut(&"settings".into())?;
    let mut seen_cell = false;
    visit_cells(settings, 0, &mut |cell| {
        seen_cell = true;
        visit(cell)
    })?;
    if !seen_cell {
        return None;
    }
    if let Some(Tag::Compound(mapper)) = generator.get_mut(&"biome_source".into())
        && declared_type(mapper, "terraforged:classic")
    {
        visit(mapper)?;
        return Some(true);
    }
    Some(false)
}

fn read_overrides(dimensions: &mut Compound) -> Option<(Map<String, Value>, bool)> {
    let mut active = None;
    let classic = visit_targets(dimensions, |node| {
        let overrides = match node.get(&"preset".into()) {
            None => Map::new(),
            Some(Tag::Compound(fields)) if fields.len() <= FIELDS.len() => fields
                .iter()
                .map(|(key, value)| {
                    let key = key.to_string().ok()?;
                    let value = match value {
                        Tag::Byte(value @ (0 | 1)) => Value::Bool(*value == 1),
                        Tag::Short(value) => Value::from(*value),
                        Tag::Int(value) => Value::from(*value),
                        Tag::Long(value) => Value::from(*value),
                        Tag::Float(value) => Value::from(f32::from_bits(*value)),
                        Tag::Double(value) => Value::from(f64::from_bits(*value)),
                        _ => return None,
                    };
                    Some((key, value))
                })
                .collect::<Option<Map<_, _>>>()?,
            _ => return None,
        };
        if active.as_ref().is_some_and(|first| first != &overrides) {
            return None;
        }
        active = Some(overrides);
        Some(())
    })?;
    Some((active?, classic))
}

fn write_overrides(dimensions: &mut Compound, overrides: &Map<String, Value>) -> bool {
    let config = overrides
        .iter()
        .map(|(key, value)| {
            let value = match value {
                Value::Bool(value) => Tag::Byte(i8::from(*value)),
                Value::Number(value) => match value.as_i64() {
                    Some(value) => Tag::Long(value),
                    None => Tag::Double(value.as_f64()?.to_bits()),
                },
                _ => return None,
            };
            Some((key.as_str().into(), value))
        })
        .collect::<Option<Compound>>();
    let Some(config) = config else {
        return false;
    };
    visit_targets(dimensions, |node| {
        if config.is_empty() {
            node.remove(&"preset".into());
        } else {
            node.insert("preset".into(), Tag::Compound(config.clone()));
        }
        Some(())
    })
    .is_some()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn editor_copies_only_its_own_terrain_settings_and_resets_to_defaults() {
        let cell = Tag::compound([("type", Tag::String("terraforged:cell".into()))]);
        let mapper = Tag::compound([("type", Tag::String("terraforged:classic".into()))]);
        let vanilla = Tag::compound([("type", Tag::String("minecraft:constant".into()))]);
        let overworld = Tag::compound([(
            "generator",
            Tag::compound([
                (
                    "settings",
                    Tag::List(vec![vanilla.clone(), cell.clone(), cell.clone()]),
                ),
                ("biome_source", mapper.clone()),
            ]),
        )]);
        let initial = Compound::from([
            ("minecraft:overworld".into(), overworld.clone()),
            ("minecraft:the_nether".into(), overworld),
        ]);
        let mut dims = initial.clone();
        let edits = Map::from_iter([
            ("/world/continent/continentScale".into(), Value::from(4200)),
            (
                "/terrain/general/globalVerticalScale".into(),
                Value::from(0.625),
            ),
            ("/terrain/general/fancyMountains".into(), Value::Bool(false)),
        ]);
        assert_eq!(read_overrides(&mut dims), Some((Map::new(), true)));
        assert!(write_overrides(&mut dims, &edits));
        assert_eq!(read_overrides(&mut dims), Some((edits, true)));
        assert_eq!(
            dims.get(&"minecraft:the_nether".into()),
            initial.get(&"minecraft:the_nether".into())
        );
        let generator = dims
            .get(&"minecraft:overworld".into())
            .unwrap()
            .get("generator")
            .unwrap();
        let Some(Tag::List(nodes)) = generator.get("settings") else {
            panic!("settings")
        };
        assert_eq!(nodes[0], vanilla);
        assert!(nodes[1].get("preset").is_some());
        assert_eq!(nodes[1].get("preset"), nodes[2].get("preset"));
        assert_eq!(
            nodes[1].get("preset"),
            generator.get("biome_source").unwrap().get("preset")
        );
        assert!(write_overrides(&mut dims, &Map::new()));
        assert_eq!(dims, initial);
    }

    #[test]
    fn asymmetric_packs_cannot_be_overwritten_by_an_editor_session() {
        let node = |value| {
            Tag::compound([
                ("type", Tag::String("terraforged:cell".into())),
                (
                    "preset",
                    Tag::compound([("/rivers/riverCount", Tag::Int(value))]),
                ),
            ])
        };
        let mut dims = Compound::from([(
            "minecraft:overworld".into(),
            Tag::compound([(
                "generator",
                Tag::compound([("settings", Tag::List(vec![node(5), node(6)]))]),
            )]),
        )]);
        assert!(read_overrides(&mut dims).is_none());
    }
}

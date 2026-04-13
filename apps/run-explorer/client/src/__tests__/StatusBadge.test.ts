import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusBadge from '../components/StatusBadge.vue'

describe('StatusBadge', () => {
  it('renders a green dot class (bg-emerald-500) for PASS status', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'PASS' } })
    const dot = wrapper.find('span.bg-emerald-500')
    expect(dot.exists()).toBe(true)
  })

  it('renders a red dot class (bg-red-500) for FAIL status', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'FAIL' } })
    const dot = wrapper.find('span.bg-red-500')
    expect(dot.exists()).toBe(true)
  })
})
